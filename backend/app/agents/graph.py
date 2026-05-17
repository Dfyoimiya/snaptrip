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

from app.agents.context_loader import ContextLoader
from app.agents.execution_engine import ExecutionEngine
from app.agents.fallback_engine import FallbackEngine
from app.agents.intent_parser import IntentParser
from app.agents.memory_manager import MemoryManager
from app.agents.notify_engine import NotifyEngine
from app.agents.planning_engine import PlanningEngine
from app.agents.protocol import AgentContext, AgentResult
from app.agents.retrieval_engine import RetrievalEngine
from app.core.constants import FALLBACK_MAX_RETRY, PlanStatus

logger = logging.getLogger(__name__)


def _ar(key: str, data: dict[str, Any]) -> AgentResult:
    """快捷构造 AgentResult 用于 history 链。"""
    return AgentResult(agent_name=key, status="success", data=data)


class PlanState(TypedDict, total=False):
    plan_id: str
    session_id: str
    user_id: str
    user_input: str
    lat: float
    lng: float
    status: str

    intent: dict[str, Any] | None
    enriched_intent: dict[str, Any] | None
    candidates: dict[str, Any] | None
    draft: dict[str, Any] | None
    execution: dict[str, Any] | None
    fallback_revision: dict[str, Any] | None
    share_card: dict[str, Any] | None

    user_decision: str | None
    fallback_count: int
    errors: list[dict[str, Any]]


def _context_from_state(state: PlanState, history: list[AgentResult] | None = None) -> AgentContext:
    return AgentContext(
        plan_id=state.get("plan_id", ""),
        session_id=state.get("session_id", ""),
        user_id=state.get("user_id", "default"),
        user_input=state.get("user_input", ""),
        lat=state.get("lat", 39.9219),
        lng=state.get("lng", 116.4435),
        state=state.get("status", PlanStatus.IDLE),
        history=history or [],
    )


async def intent_parser_node(state: PlanState) -> dict[str, Any]:
    agent = IntentParser()
    context = _context_from_state(state)
    result = await agent.execute(context)
    intent_data = result.data.get("intent", {})
    return {
        "intent": intent_data,
        "status": PlanStatus.DRAFTING,
    }


async def context_loader_node(state: PlanState) -> dict[str, Any]:
    agent = ContextLoader()
    history = [_ar("intent_parser", {"intent": state.get("intent", {})})]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    enriched = result.data.get("enriched_intent", {})
    return {"enriched_intent": enriched}


async def memory_manager_node(state: PlanState) -> dict[str, Any]:
    agent = MemoryManager()
    enriched = state.get("enriched_intent", {})
    history = [
        _ar("intent_parser", {"intent": state.get("intent", {})}),
        _ar("context_loader", {"enriched_intent": enriched}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    enhanced = result.data.get("enriched_intent", state.get("enriched_intent", {}))
    return {"enriched_intent": enhanced}


async def retrieval_engine_node(state: PlanState) -> dict[str, Any]:
    agent = RetrievalEngine()
    enriched = state.get("enriched_intent", {})
    history = [
        _ar("intent_parser", {"intent": state.get("intent", {})}),
        _ar("context_loader", {"enriched_intent": enriched}),
        _ar("memory_manager", {"enriched_intent": enriched}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    candidates = result.data.get("candidates", {})
    return {
        "candidates": candidates,
        "status": PlanStatus.PLANNING,
    }


async def planning_engine_node(state: PlanState) -> dict[str, Any]:
    agent = PlanningEngine()
    enriched = state.get("enriched_intent", {})
    history = [
        _ar("intent_parser", {"intent": state.get("intent", {})}),
        _ar("context_loader", {"enriched_intent": enriched}),
        _ar("memory_manager", {"enriched_intent": enriched}),
        _ar("retrieval_engine", {"candidate_pool": state.get("candidates", {})}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    draft = result.data.get("draft", {})
    return {
        "draft": draft,
        "status": PlanStatus.CONFIRMING,
    }


async def consensus_resolver_node(state: PlanState) -> dict[str, Any]:
    from app.agents.consensus_resolver import ConsensusResolver
    agent = ConsensusResolver()
    history = [
        AgentResult(agent_name="planning_engine", status="success", data={"draft": state.get("draft", {})}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    decision = result.data.get("status", "confirmed")
    return {"user_decision": decision}


def route_consensus(state: PlanState) -> Literal["execution_engine", "planning_engine", "end"]:
    decision = state.get("user_decision", "confirmed")
    if decision == "confirmed":
        return "execution_engine"
    if decision == "objection":
        return "planning_engine"
    return "end"


async def execution_engine_node(state: PlanState) -> dict[str, Any]:
    agent = ExecutionEngine()
    history = [
        AgentResult(agent_name="planning_engine", status="success", data={"draft": state.get("draft", {})}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    exec_data = result.data.get("execution", {})
    return {
        "execution": exec_data,
        "status": PlanStatus.EXECUTING,
    }


def route_execution(state: PlanState) -> Literal["notify_engine", "fallback_engine", "end"]:
    exec_data = state.get("execution", {})
    status = exec_data.get("status", "full_success")
    if status == "full_success":
        return "notify_engine"
    if status == "partial_success" and state.get("fallback_count", 0) < FALLBACK_MAX_RETRY:
        return "fallback_engine"
    return "end"


async def fallback_engine_node(state: PlanState) -> dict[str, Any]:
    agent = FallbackEngine()
    history = [
        AgentResult(agent_name="planning_engine", status="success", data={"draft": state.get("draft", {})}),
        AgentResult(agent_name="execution_engine", status="success", data={"execution": state.get("execution", {})}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    revision = result.data.get("revision", result.data.get("revised_plan"))
    new_count = state.get("fallback_count", 0) + 1
    return {
        "fallback_revision": revision,
        "fallback_count": new_count,
    }


def route_fallback(state: PlanState) -> Literal["planning_engine", "end"]:
    revision = state.get("fallback_revision")
    if revision and state.get("fallback_count", 0) < FALLBACK_MAX_RETRY:
        return "planning_engine"
    return "end"


async def notify_engine_node(state: PlanState) -> dict[str, Any]:
    agent = NotifyEngine()
    history = [
        AgentResult(agent_name="planning_engine", status="success", data={"draft": state.get("draft", {})}),
        AgentResult(agent_name="execution_engine", status="success", data={"execution": state.get("execution", {})}),
    ]
    context = _context_from_state(state, history)
    result = await agent.execute(context)
    share_card = result.data.get("share_card", {})
    return {
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
