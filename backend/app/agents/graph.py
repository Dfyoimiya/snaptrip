"""LangGraph StateGraph —— 竞赛核心 Agent 编排图。

定义 9 个 Agent Node + 条件边，替代 plan.py 中的硬编码串行调用。
接入 PostgresSaver 获得状态持久化与断点恢复能力。

Node 清单:
  intent_parser → context_loader → memory_manager
  → retrieval_engine → planning_engine → consensus_resolver
  → execution_engine → [fallback_engine] → notify_engine

条件边:
  consensus_resolver ──[confirmed]→ execution_engine
                     ──[objection]→ planning_engine (增量重规划)
  execution_engine   ──[full_success]→ notify_engine
                     ──[partial_success]→ fallback_engine
                     ──[full_failure]→ END
  fallback_engine    ──[retry]→ planning_engine
                     ──[exhausted]→ END

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from app.agent_runtime.events import build_runtime_event
from app.agent_runtime.postconfirm_state import (
    build_repair_state,
    confirmation_from_resume,
    maybe_apply_confirmation_replan,
    notification_state_from_share_card,
    route_from_confirmation,
)
from app.agent_runtime.preconfirm_state import (
    build_memory_features as _build_memory_features,
)
from app.agent_runtime.preconfirm_state import (
    candidate_pool_from_state as _candidate_pool_from_state,
)
from app.agent_runtime.preconfirm_state import (
    context_from_state as _context_from_state,
)
from app.agent_runtime.preconfirm_state import (
    context_profile_from_state as _context_profile_from_state,
)
from app.agent_runtime.preconfirm_state import (
    make_agent_result as _ar,
)
from app.agent_runtime.preconfirm_state import (
    pending_confirmation,
)
from app.agents.consensus_resolver import ConsensusResolver
from app.agents.context_loader import ContextLoader
from app.agents.execution_engine import ExecutionEngine
from app.agents.fallback_engine import FallbackEngine
from app.agents.intent_parser import IntentParser
from app.agents.memory_manager import MemoryManager
from app.agents.notify_engine import NotifyEngine
from app.agents.planning_engine import PlanningEngine
from app.agents.protocol import AgentResult
from app.agents.retrieval_engine import RetrievalEngine
from app.core.constants import FALLBACK_MAX_RETRY, PlanStatus
from app.ports.events import EventSinkPort
from app.schemas.agent.events import RuntimeEventType

logger = logging.getLogger(__name__)

_gateway = None
_event_sink: EventSinkPort | None = None


def set_gateway(gateway) -> None:
    global _gateway
    _gateway = gateway


def set_event_sink(event_sink: EventSinkPort | None) -> None:
    global _event_sink
    _event_sink = event_sink


class PlanState(TypedDict, total=False):
    """LangGraph 运行时状态定义。

    字段说明:
      - request: PlanRequestEnvelope 的字典形式
      - plan_id / session_id / user_id / user_input / lat / lng: 请求元数据
      - status: 当前 PlanRuntimeStatus
      - intent: IntentParser 输出 (IntentSchema dict)
      - context_profile: ContextLoader + MemoryManager 增强后的画像 (EnrichedIntent dict)
      - memory_features: MemoryManager 聚合的统计特征 (MemoryFeatures dict)
      - candidate_pool: RetrievalEngine 召回的候选 POI (CandidatePool dict)
      - draft: PlanningEngine 生成的计划草案 (PlanDraft dict)
      - confirmation: 人机协同确认状态 (ConfirmationState dict)
      - execution: ExecutionEngine 原始执行结果 (ExecutionResult dict)
      - execution_state: 规范化执行状态 (ExecutionState dict)
      - fallback_revision: FallbackEngine 产生的修订方案 (RevisedPlan dict)
      - repair: 修复/重规划生命周期状态 (RepairState dict)
      - notification: NotifyEngine 输出 (NotificationState dict)
      - share_card: 分享卡片 (ShareCard dict，兼容旧响应)
      - locked_slots: 用户锁定的 slot 索引
      - fallback_count: fallback 重试计数
      - errors: 结构化错误列表 (AgentError dict)
    """

    request: dict[str, Any] | None
    plan_id: str
    session_id: str
    user_id: str
    user_input: str
    lat: float
    lng: float
    status: str

    intent: dict[str, Any] | None
    context_profile: dict[str, Any] | None
    memory_features: dict[str, Any] | None
    candidate_pool: dict[str, Any] | None
    draft: dict[str, Any] | None
    confirmation: dict[str, Any] | None
    execution: dict[str, Any] | None
    execution_state: dict[str, Any] | None
    fallback_revision: dict[str, Any] | None
    repair: dict[str, Any] | None
    notification: dict[str, Any] | None
    share_card: dict[str, Any] | None

    locked_slots: list[int]
    user_decision: str | None
    fallback_count: int
    errors: list[dict[str, Any]]


async def _emit_node_event(
    state: PlanState,
    *,
    node_name: str,
    event_type: RuntimeEventType,
    payload: dict[str, Any] | None = None,
) -> None:
    if _event_sink is None:
        return
    request = state.get("request") or {}
    run_id = request.get("request_id") or state.get("plan_id", "")
    plan_id = state.get("plan_id") or request.get("plan_id", "")
    event = build_runtime_event(
        run_id=run_id,
        plan_id=plan_id,
        node_name=node_name,
        event_type=event_type,
        payload=payload or {},
    )
    await _event_sink.emit(event)


async def intent_parser_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="intent_parser", event_type="node_started")
    agent = IntentParser()
    context = _context_from_state(state)
    result = await agent.execute(context)
    intent_data = result.data.get("intent", {})
    await _emit_node_event(
        state,
        node_name="intent_parser",
        event_type="node_succeeded",
        payload={"city": intent_data.get("city"), "confidence": intent_data.get("confidence")},
    )
    return {
        "intent": intent_data,
        "status": PlanStatus.DRAFTING,
    }


async def context_loader_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="context_loader", event_type="node_started")
    agent = ContextLoader()
    history = [_ar("intent_parser", {"intent": state.get("intent", {})})]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    enriched = result.data.get("enriched_intent", {})
    await _emit_node_event(
        state,
        node_name="context_loader",
        event_type="node_succeeded",
        payload={"has_profile_vector": bool(enriched.get("profile_vector"))},
    )
    return {
        "context_profile": enriched,
    }


async def memory_manager_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="memory_manager", event_type="node_started")
    agent = MemoryManager()
    enriched = _context_profile_from_state(state)
    history = [
        _ar("intent_parser", {"intent": state.get("intent", {})}),
        _ar("context_loader", {"context_profile": enriched}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    enhanced = result.data.get("enriched_intent", _context_profile_from_state(state))
    memory_features = _build_memory_features(enhanced)
    await _emit_node_event(
        state,
        node_name="memory_manager",
        event_type="node_succeeded",
        payload={"dominant_scene": memory_features.get("dominant_scene")},
    )
    return {
        "context_profile": enhanced,
        "memory_features": memory_features,
    }


async def retrieval_engine_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="retrieval_engine", event_type="node_started")
    agent = RetrievalEngine()
    enriched = _context_profile_from_state(state)
    history = [
        _ar("intent_parser", {"intent": state.get("intent", {})}),
        _ar("context_loader", {"context_profile": enriched}),
        _ar("memory_manager", {"context_profile": enriched}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    candidates = result.data.get("candidate_pool", {})
    await _emit_node_event(
        state,
        node_name="retrieval_engine",
        event_type="node_succeeded",
        payload={"candidate_count": len(candidates.get("candidates", []))},
    )
    return {
        "candidate_pool": candidates,
        "status": PlanStatus.PLANNING,
    }


async def planning_engine_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="planning_engine", event_type="node_started")
    revised_draft = maybe_apply_confirmation_replan(state)
    if revised_draft is not None:
        await _emit_node_event(
            state,
            node_name="planning_engine",
            event_type="node_succeeded",
            payload={"slot_count": len(revised_draft.get("slots", [])), "source": "confirmation_replan"},
        )
        return {
            "draft": revised_draft,
            "repair": build_repair_state(
                draft=state.get("draft"),
                revision={"plan": revised_draft, "diff_patch": []},
                locked_slots=(state.get("confirmation") or {}).get("locked_slots", []),
                retry_count=state.get("fallback_count", 0),
            ),
            "confirmation": pending_confirmation(),
            "status": PlanStatus.CONFIRMING,
        }

    repair = state.get("repair") or {}
    revised_from_fallback = repair.get("revised_draft")
    if revised_from_fallback:
        revised_dump = (
            revised_from_fallback.model_dump()
            if hasattr(revised_from_fallback, "model_dump")
            else revised_from_fallback
        )
        await _emit_node_event(
            state,
            node_name="planning_engine",
            event_type="node_succeeded",
            payload={"slot_count": len(revised_dump.get("slots", [])), "source": "fallback_repair"},
        )
        return {
            "draft": revised_dump,
            "confirmation": pending_confirmation(),
            "status": PlanStatus.CONFIRMING,
        }

    agent = PlanningEngine()
    enriched = _context_profile_from_state(state)
    history = [
        _ar("intent_parser", {"intent": state.get("intent", {})}),
        _ar("context_loader", {"enriched_intent": enriched}),
        _ar("memory_manager", {"enriched_intent": enriched}),
        _ar("retrieval_engine", {"candidate_pool": _candidate_pool_from_state(state)}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    draft = result.data.get("draft", {})
    await _emit_node_event(
        state,
        node_name="planning_engine",
        event_type="node_succeeded",
        payload={"slot_count": len(draft.get("slots", [])), "total_cost": draft.get("total_cost", 0)},  # type: ignore[union-attr]
    )
    return {
        "draft": draft,
        "confirmation": pending_confirmation(),
        "status": PlanStatus.CONFIRMING,
    }


async def consensus_resolver_node(state: PlanState) -> dict[str, Any]:
    draft = state.get("draft", {})

    # 调用 ConsensusResolver 做预分析
    agent = ConsensusResolver()
    history = [
        AgentResult(agent_name="planning_engine", status="success", data={"draft": draft}),
    ]
    context = _context_from_state(state, history)
    resolver_result = await agent.execute(context)
    rationale = resolver_result.data.get("rationale", "请确认或修改计划")

    await _emit_node_event(
        state,
        node_name="consensus_resolver",
        event_type="interrupt_requested",
        payload={
            "slot_count": len(draft.get("slots", [])),  # type: ignore[union-attr]
            "suggested_decision": resolver_result.data.get("decision"),
            "rationale": rationale,
        },
    )
    user_choice = interrupt(
        {
            "event": "consensus",
            "draft": draft,
            "message": rationale,
            "suggested_decision": resolver_result.data.get("decision"),
        }
    )
    decision = user_choice.get("decision", "confirmed") if isinstance(user_choice, dict) else "confirmed"
    confirmation = confirmation_from_resume(user_choice if isinstance(user_choice, dict) else {"decision": "confirmed"})
    await _emit_node_event(
        state,
        node_name="consensus_resolver",
        event_type="interrupt_resumed",
        payload={"decision": decision},
    )
    return {
        "user_decision": decision,
        "confirmation": confirmation,
        "locked_slots": confirmation.get("locked_slots", []),
    }


def route_consensus(state: PlanState) -> Literal["execution_engine", "planning_engine", "end"]:
    return route_from_confirmation(state)


async def execution_engine_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="execution_engine", event_type="node_started")
    agent = ExecutionEngine(gateway=_gateway)
    history = [
        AgentResult(agent_name="planning_engine", status="success", data={"draft": state.get("draft", {})}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    exec_data = result.data.get("execution", {})
    execution_state = result.data.get("execution_state", {})
    await _emit_node_event(
        state,
        node_name="execution_engine",
        event_type="node_succeeded",
        payload={"status": exec_data.get("status", "unknown"), "failed_count": len(exec_data.get("failed_slots", []))},
    )
    return {
        "execution": exec_data,
        "execution_state": execution_state,
        "status": PlanStatus.EXECUTING,
    }


def route_execution(state: PlanState) -> Literal["notify_engine", "fallback_engine", "end"]:
    exec_data: dict[str, Any] = state.get("execution") or {}
    status = exec_data.get("status", "full_success")
    if status == "full_success":
        return "notify_engine"
    if status == "partial_success" and state.get("fallback_count", 0) < FALLBACK_MAX_RETRY:
        return "fallback_engine"
    return "end"


async def fallback_engine_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="fallback_engine", event_type="node_started")
    agent = FallbackEngine()
    history = [
        AgentResult(agent_name="planning_engine", status="success", data={"draft": state.get("draft", {})}),
        AgentResult(agent_name="execution_engine", status="success", data={"execution": state.get("execution", {})}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    revision = result.data.get("revision", result.data.get("revised_plan"))
    new_count = state.get("fallback_count", 0) + 1
    await _emit_node_event(
        state,
        node_name="fallback_engine",
        event_type="node_succeeded",
        payload={"retry_count": new_count, "has_revision": bool(revision)},
    )
    return {
        "draft": (revision or {}).get("plan", state.get("draft", {}))
        if isinstance(revision, dict)
        else state.get("draft", {}),
        "fallback_revision": revision,
        "repair": build_repair_state(
            draft=state.get("draft"),
            revision=revision,
            locked_slots=state.get("locked_slots", []),
            retry_count=new_count,
        ),
        "fallback_count": new_count,
    }


def route_fallback(state: PlanState) -> Literal["planning_engine", "end"]:
    revision = state.get("fallback_revision")
    if revision and state.get("fallback_count", 0) < FALLBACK_MAX_RETRY:
        return "planning_engine"
    return "end"


async def notify_engine_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="notify_engine", event_type="node_started")
    agent = NotifyEngine()
    history = [
        AgentResult(agent_name="planning_engine", status="success", data={"draft": state.get("draft", {})}),
        AgentResult(agent_name="execution_engine", status="success", data={"execution": state.get("execution", {})}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    share_card = result.data.get("share_card", {})
    await _emit_node_event(
        state,
        node_name="notify_engine",
        event_type="node_succeeded",
        payload={"has_share_card": bool(share_card)},
    )
    await _emit_node_event(
        state,
        node_name="plan",
        event_type="plan_completed",
        payload={"status": PlanStatus.DONE},
    )
    return {
        "notification": notification_state_from_share_card(share_card),
        "share_card": share_card,
        "status": PlanStatus.DONE,
    }


def build_plan_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    graph = StateGraph(PlanState)

    graph.add_node("intent_parser", intent_parser_node)
    graph.add_node("context_loader", context_loader_node)
    graph.add_node("memory_manager", memory_manager_node)
    graph.add_node("retrieval_engine", retrieval_engine_node)
    graph.add_node("planning_engine", planning_engine_node)
    graph.add_node("consensus_resolver", consensus_resolver_node)
    graph.add_node("execution_engine", execution_engine_node)
    graph.add_node("fallback_engine", fallback_engine_node)
    graph.add_node("notify_engine", notify_engine_node)

    graph.set_entry_point("intent_parser")
    graph.add_edge("intent_parser", "context_loader")
    graph.add_edge("context_loader", "memory_manager")
    graph.add_edge("memory_manager", "retrieval_engine")
    graph.add_edge("retrieval_engine", "planning_engine")
    graph.add_edge("planning_engine", "consensus_resolver")

    graph.add_conditional_edges(
        "consensus_resolver",
        route_consensus,
        {
            "execution_engine": "execution_engine",
            "planning_engine": "planning_engine",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "execution_engine",
        route_execution,
        {
            "notify_engine": "notify_engine",
            "fallback_engine": "fallback_engine",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "fallback_engine",
        route_fallback,
        {
            "planning_engine": "planning_engine",
            "end": END,
        },
    )

    graph.add_edge("notify_engine", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())


plan_graph = build_plan_graph()
