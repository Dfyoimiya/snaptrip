"""LangGraph StateGraph —— 多 Agent 与 单 Agent 双模式编排图。

模式:
  - 多 Agent (build_plan_graph): 9 节点完整编排
  - 单 Agent (build_single_agent_graph): 5 节点简化编排

v3 单 Agent 模式:
  planner (Intent+Context+Memory+Retrieval+Planning 折叠)
  → consensus (人机确认)
  → execution (v3 安全管道: CB + 幂等 + Saga + UNKNOWN 确认)
  → [fallback] (v3 孤儿取消)
  → notify

Author: SnapTrip Team
Date: 2026-05-17 / v3 update 2026-05-21
"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from snaptrip_shared.core.constants import FALLBACK_MAX_RETRY, PlanStatus

from agent_worker.app.agent.engines.consensus_resolver import ConsensusResolver
from agent_worker.app.agent.engines.context_loader import ContextLoader
from agent_worker.app.agent.engines.execution_engine import ExecutionEngine
from agent_worker.app.agent.engines.fallback_engine import FallbackEngine
from agent_worker.app.agent.engines.intent_parser import IntentParser
from agent_worker.app.agent.engines.memory_manager import MemoryManager
from agent_worker.app.agent.engines.notify_engine import NotifyEngine
from agent_worker.app.agent.engines.planning_engine import PlanningEngine
from agent_worker.app.agent.engines.retrieval_engine import RetrievalEngine
from agent_worker.app.agent.ports.events import EventSinkPort
from agent_worker.app.agent.protocol import AgentResult
from agent_worker.app.agent.runtime import AgentRuntime
from agent_worker.app.agent.schemas.events import RuntimeEventType
from agent_worker.app.agent.state.events import build_runtime_event
from agent_worker.app.agent.state.postconfirm import (
    build_repair_state,
    confirmation_from_resume,
    maybe_apply_confirmation_replan,
    notification_state_from_share_card,
    route_from_confirmation,
)
from agent_worker.app.agent.state.preconfirm import (
    build_memory_features as _build_memory_features,
)
from agent_worker.app.agent.state.preconfirm import (
    candidate_pool_from_state as _candidate_pool_from_state,
)
from agent_worker.app.agent.state.preconfirm import (
    context_from_state as _context_from_state,
)
from agent_worker.app.agent.state.preconfirm import (
    context_profile_from_state as _context_profile_from_state,
)
from agent_worker.app.agent.state.preconfirm import (
    make_agent_result as _ar,
)
from agent_worker.app.agent.state.preconfirm import (
    pending_confirmation,
)

logger = logging.getLogger(__name__)

# ── 依赖注入（Phase 1: AgentRuntime 优先，全局变量向后兼容）──
_runtime: AgentRuntime | None = None

# ── 向后兼容的全局变量（deprecated，新代码请使用 AgentRuntime）──
_gateway = None
_event_sink: EventSinkPort | None = None
_tool_adapter: Any = None
_cb_registry: Any = None
_idempotency: Any = None
_saga: Any = None
_confirmator: Any = None
_redis: Any = None


def _resolve_gateway():
    return _runtime.gateway if _runtime else _gateway


def _resolve_event_sink():
    return _runtime.event_sink if _runtime else _event_sink


def _resolve_tool_adapter():
    return _runtime.tool_adapter if _runtime else _tool_adapter


def _resolve_cb_registry():
    return _runtime.cb_registry if _runtime else _cb_registry


def _resolve_idempotency():
    return _runtime.idempotency if _runtime else _idempotency


def _resolve_saga():
    return _runtime.saga if _runtime else _saga


def _resolve_confirmator():
    return _runtime.confirmator if _runtime else _confirmator


def _resolve_redis():
    return _runtime.redis if _runtime else _redis


def _resolve_marketplace_client():
    return _runtime.marketplace_client if _runtime else None


def set_gateway(gateway) -> None:
    """[deprecated] 使用 AgentRuntime.gateway 替代。"""
    global _gateway
    _gateway = gateway


def set_event_sink(event_sink: EventSinkPort | None) -> None:
    """[deprecated] 使用 AgentRuntime.event_sink 替代。"""
    global _event_sink
    _event_sink = event_sink


def set_v3_dependencies(
    tool_adapter: Any = None,
    cb_registry: Any = None,
    idempotency: Any = None,
    saga: Any = None,
    confirmator: Any = None,
    redis: Any = None,
) -> None:
    """[deprecated] 使用 AgentRuntime 注入 v3 安全管道依赖。"""
    global _tool_adapter, _cb_registry, _idempotency, _saga, _confirmator, _redis
    _tool_adapter = tool_adapter
    _cb_registry = cb_registry
    _idempotency = idempotency
    _saga = saga
    _confirmator = confirmator
    _redis = redis


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


# ====================================================================
# Event helpers
# ====================================================================


async def _emit_node_event(
    state: PlanState,
    *,
    node_name: str,
    event_type: RuntimeEventType,
    payload: dict[str, Any] | None = None,
) -> None:
    sink = _resolve_event_sink()
    if sink is None:
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
    await sink.emit(event)


# ====================================================================
# Node: intent_parser (多 Agent 模式)
# ====================================================================


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


# ====================================================================
# Node: context_loader (多 Agent 模式)
# ====================================================================


async def context_loader_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="context_loader", event_type="node_started")
    agent = ContextLoader(user_profile_repo=_runtime.user_profile_repo if _runtime else None)
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


# ====================================================================
# Node: memory_manager (多 Agent 模式)
# ====================================================================


async def memory_manager_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="memory_manager", event_type="node_started")
    agent = MemoryManager(plan_repo=_runtime.plan_repo if _runtime else None)
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


# ====================================================================
# Node: retrieval_engine (多 Agent 模式)
# ====================================================================


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


# ====================================================================
# Node: planning_engine (多 Agent 模式)
# ====================================================================


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
        payload={"slot_count": len(draft.get("slots", [])), "total_cost": draft.get("total_cost", 0)},
    )
    return {
        "draft": draft,
        "confirmation": pending_confirmation(),
        "status": PlanStatus.CONFIRMING,
    }


# ====================================================================
# Node: consensus_resolver
# ====================================================================


async def consensus_resolver_node(state: PlanState) -> dict[str, Any]:
    draft = state.get("draft") or {}

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
            "slot_count": len(draft.get("slots", [])),
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


# ====================================================================
# Node: execution_engine (v3 增强)
# ====================================================================


async def execution_engine_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="execution_engine", event_type="node_started")

    # v3 安全管道: 优先使用 AgentRuntime，回退到旧版全局变量
    agent = ExecutionEngine(
        tool_adapter=_resolve_tool_adapter(),
        circuit_breaker_registry=_resolve_cb_registry(),
        idempotency=_resolve_idempotency(),
        saga=_resolve_saga(),
        confirmator=_resolve_confirmator(),
        redis_client=_resolve_redis(),
        gateway=_resolve_gateway(),
    )

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


# ====================================================================
# Node: fallback_engine (v3 增强)
# ====================================================================


async def fallback_engine_node(state: PlanState) -> dict[str, Any]:
    await _emit_node_event(state, node_name="fallback_engine", event_type="node_started")

    # v3 孤儿取消: 注入 ToolAdapter + Saga（优先 AgentRuntime）
    agent = FallbackEngine(
        tool_adapter=_resolve_tool_adapter(),
        saga=_resolve_saga(),
    )

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


# ====================================================================
# Node: notify_engine
# ====================================================================


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


# ====================================================================
# Graph: 9 节点多 Agent 模式 (向后兼容)
# ====================================================================


def build_plan_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    runtime: AgentRuntime | None = None,
) -> CompiledStateGraph:
    """构建 9 节点多 Agent 编排图。

    Args:
        checkpointer: LangGraph checkpoint 存储。
        runtime: 依赖注入容器。为 None 时使用全局变量（向后兼容）。

    Node 清单:
      intent_parser → context_loader → memory_manager
      → retrieval_engine → planning_engine → consensus_resolver
      → execution_engine → [fallback_engine] → notify_engine
    """
    global _runtime
    if runtime is not None:
        _runtime = runtime

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


# ====================================================================
# Graph: 5 节点单 Agent 模式 (v3)
# ====================================================================

# ── Planner Node (折叠 intent+context+memory+retrieval+planning) ──


async def planner_node(state: PlanState) -> dict[str, Any]:
    """单 Agent 规划节点 —— 折叠多 Agent 的前 5 个节点。

    流程:
      1. IntentParser → 意图解析
      2. ContextLoader → 上下文加载
      3. MemoryManager → 记忆聚合
      4. RetrievalEngine → 候选召回
      5. PlanningEngine → 计划生成

    合并为一个节点以减少状态传递开销和序列化成本。
    """
    await _emit_node_event(state, node_name="planner", event_type="node_started")

    # ── 检查是否有 fallback 修订或用户变更请求 ──
    revised_draft = maybe_apply_confirmation_replan(state)
    if revised_draft is not None:
        await _emit_node_event(
            state,
            node_name="planner",
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
            node_name="planner",
            event_type="node_succeeded",
            payload={"slot_count": len(revised_dump.get("slots", [])), "source": "fallback_repair"},
        )
        return {
            "draft": revised_dump,
            "confirmation": pending_confirmation(),
            "status": PlanStatus.CONFIRMING,
        }

    # ── 折叠执行 5 个 Agent ──
    ctx = _context_from_state(state)

    # 1. Intent Parser
    intent_agent = IntentParser()
    intent_result = await intent_agent.execute(ctx)
    intent_data = intent_result.data.get("intent", {})
    logger.info("planner_collapsed intent_parser done city=%s", intent_data.get("city"))

    # 2. Context Loader
    ctx_loader = ContextLoader(user_profile_repo=_runtime.user_profile_repo if _runtime else None)
    ctx_result = await ctx_loader.execute(_context_from_state(state, [_ar("intent_parser", {"intent": intent_data})]))
    enriched = ctx_result.data.get("enriched_intent", {})
    logger.info("planner_collapsed context_loader done")

    # 3. Memory Manager
    mem_agent = MemoryManager(plan_repo=_runtime.plan_repo if _runtime else None)
    mem_result = await mem_agent.execute(
        _context_from_state(
            state,
            [
                _ar("intent_parser", {"intent": intent_data}),
                _ar("context_loader", {"context_profile": enriched}),
            ],
        )
    )
    enhanced_enriched = mem_result.data.get("enriched_intent", enriched)
    memory_features = _build_memory_features(enhanced_enriched)
    logger.info("planner_collapsed memory_manager done scene=%s", memory_features.get("dominant_scene"))

    # 4. Retrieval Engine
    ret_agent = RetrievalEngine()
    ret_result = await ret_agent.execute(
        _context_from_state(
            state,
            [
                _ar("intent_parser", {"intent": intent_data}),
                _ar("context_loader", {"context_profile": enhanced_enriched}),
                _ar("memory_manager", {"context_profile": enhanced_enriched}),
            ],
        )
    )
    candidates = ret_result.data.get("candidate_pool", {})
    logger.info("planner_collapsed retrieval done count=%d", len(candidates.get("candidates", [])))

    # 5. Planning Engine
    plan_agent = PlanningEngine()
    plan_result = await plan_agent.execute(
        _context_from_state(
            state,
            [
                _ar("intent_parser", {"intent": intent_data}),
                _ar("context_loader", {"enriched_intent": enhanced_enriched}),
                _ar("memory_manager", {"enriched_intent": enhanced_enriched}),
                _ar("retrieval_engine", {"candidate_pool": candidates}),
            ],
        )
    )
    draft = plan_result.data.get("draft", {})
    logger.info("planner_collapsed planning done slots=%d", len(draft.get("slots", [])))

    await _emit_node_event(
        state,
        node_name="planner",
        event_type="node_succeeded",
        payload={"slot_count": len(draft.get("slots", [])), "total_cost": draft.get("total_cost", 0)},
    )

    return {
        "intent": intent_data,
        "context_profile": enhanced_enriched,
        "memory_features": memory_features,
        "candidate_pool": candidates,
        "draft": draft,
        "confirmation": pending_confirmation(),
        "status": PlanStatus.CONFIRMING,
    }


async def consensus_node(state: PlanState) -> dict[str, Any]:
    """单 Agent 模式的 consensus 节点（薄封装）。"""
    return await consensus_resolver_node(state)


def route_single_consensus(state: PlanState) -> Literal["execution", "planner", "end"]:
    """单 Agent 模式 consensus 路由。"""
    result = route_from_confirmation(state)
    # 映射旧节点名 → 新节点名
    _map: dict[str, Literal["execution", "planner", "end"]] = {
        "execution_engine": "execution",
        "planning_engine": "planner",
        "end": "end",
    }
    return _map[result]


async def execution_node(state: PlanState) -> dict[str, Any]:
    """单 Agent 模式的 execution 节点（薄封装）。"""
    return await execution_engine_node(state)


def route_single_execution(state: PlanState) -> Literal["notify", "fallback", "end"]:
    """单 Agent 模式 execution 路由。"""
    result = route_execution(state)
    _map: dict[str, Literal["notify", "fallback", "end"]] = {
        "notify_engine": "notify",
        "fallback_engine": "fallback",
        "end": "end",
    }
    return _map[result]


async def fallback_node(state: PlanState) -> dict[str, Any]:
    """单 Agent 模式的 fallback 节点（薄封装）。"""
    return await fallback_engine_node(state)


def route_single_fallback(state: PlanState) -> Literal["planner", "end"]:
    """单 Agent 模式 fallback 路由。"""
    result = route_fallback(state)
    _map: dict[str, Literal["planner", "end"]] = {
        "planning_engine": "planner",
        "end": "end",
    }
    return _map[result]


async def notify_node(state: PlanState) -> dict[str, Any]:
    """单 Agent 模式的 notify 节点（薄封装）。"""
    return await notify_engine_node(state)


def build_single_agent_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    runtime: AgentRuntime | None = None,
) -> CompiledStateGraph:
    """构建 5 节点单 Agent 编排图 (v3)。

    Args:
        checkpointer: LangGraph checkpoint 存储。
        runtime: 依赖注入容器。为 None 时使用全局变量（向后兼容）。

    Node 清单:
      planner → consensus → execution → [fallback] → notify

    相比 9 节点模式:
      - intent_parser + context_loader + memory_manager + retrieval_engine + planning_engine
        → 折叠为单个 planner 节点（减少状态传递和序列化开销）
      - consensus + execution + fallback + notify 保持不变
      - execution 节点自动使用 v3 安全管道（如果通过 AgentRuntime 或 set_v3_dependencies 注入了依赖）
    """
    global _runtime
    if runtime is not None:
        _runtime = runtime

    graph = StateGraph(PlanState)

    graph.add_node("planner", planner_node)
    graph.add_node("consensus", consensus_node)
    graph.add_node("execution", execution_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("notify", notify_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "consensus")

    graph.add_conditional_edges(
        "consensus",
        route_single_consensus,
        {
            "execution": "execution",
            "planner": "planner",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "execution",
        route_single_execution,
        {
            "notify": "notify",
            "fallback": "fallback",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "fallback",
        route_single_fallback,
        {
            "planner": "planner",
            "end": END,
        },
    )

    graph.add_edge("notify", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())


# ====================================================================
# Module-level graph instances
# ====================================================================

plan_graph = build_plan_graph()
single_agent_graph = build_single_agent_graph()
