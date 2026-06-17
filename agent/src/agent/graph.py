# ────────────────────────────────────────────────────────────────────────────
# 🔵 FRAMEWORK — Agent DAG Workflow Builder
# ────────────────────────────────────────────────────────────────────────────
# Supervisor + conditional routing topology:
#
#   START → supervisor → route_by_intent:
#     ├─ product_discovery → tool_node ⇄ product_discovery → synthesize → END
#     ├─ order_assistant   → tool_node ⇄ order_assistant   → synthesize → END
#     ├─ customer_service  → tool_node ⇄ customer_service  → synthesize → END
#     ├─ marketing_engine  → tool_node ⇄ marketing_engine  → synthesize → END
#     ├─ admin_analyst     → tool_node ⇄ admin_analyst     → synthesize → END
#     └─ knowledge_qa     → tool_node ⇄ knowledge_qa     → synthesize → END
#
# Archived: 2026-06-07 — repurposed from trip planning agent
# ────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.nodes.supervisor import route_by_intent, supervisor_node
from agent.nodes.product_discovery import product_discovery_node
from agent.nodes.order_assistant import order_assistant_node
from agent.nodes.customer_service import customer_service_node
from agent.nodes.marketing_engine import marketing_engine_node
from agent.nodes.knowledge_qa import knowledge_qa_node
from agent.nodes.admin_analyst import admin_analyst_node
from agent.nodes.compliance import compliance_node
from agent.nodes.synthesize import synthesize_node
from agent.runtime import AgentRuntime
from agent.schemas.state import PlanState
from agent.tool_node import tool_node
from agent.utils import get_llm_adapter
from snaptrip_shared.core.config import settings

logger = logging.getLogger(__name__)

# ── Global DI ──
_runtime: AgentRuntime | None = None

# ── Specialist nodes (for dynamic lookup) ────────────────────────────────────

_SPECIALISTS = [
    "product_discovery",
    "order_assistant",
    "customer_service",
    "marketing_engine",
    "knowledge_qa",
    "admin_analyst",
]


# ── Conditional routing ─────────────────────────────────────────────────────


def route_after_specialist(state: PlanState) -> Literal["tools", "synthesize"]:
    """After specialist node: if tool_calls exist -> tools, else -> synthesize."""
    msgs = state.get("messages", [])
    if not msgs:
        return "synthesize"
    last_msg = msgs[-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    return "tools" if tool_calls else "synthesize"


def route_after_tools(state: PlanState) -> str:
    """After tool execution: return to the current specialist agent."""
    current = state.get("current_agent", "product_discovery")
    # Validate that the current_agent is a known specialist
    if current in _SPECIALISTS:
        return current  # type: ignore[no-any-return]
    logger.warning(
        "route_after_tools: unknown current_agent=%s, falling back to product_discovery",
        current,
    )
    return "product_discovery"


# ── Graph builder ───────────────────────────────────────────────────────────


async def build_graph(runtime: AgentRuntime | None = None) -> CompiledStateGraph:
    """Build the agent DAG with Supervisor + 6 specialist agents.

    Topology:
      START -> supervisor -> route_by_intent ->
        product_discovery | order_assistant | customer_service |
        marketing_engine | knowledge_qa | admin_analyst
      -> route_after_specialist -> tools | synthesize
      tools -> route_after_tools -> back to specialist
      synthesize -> END

    Args:
        runtime: optional DI container (AgentRuntime)

    Returns:
        CompiledStateGraph with PostgresSaver (or MemorySaver fallback)
    """
    global _runtime
    _runtime = runtime

    # ── Initialize ToolHarness + SessionContext ──
    if runtime and runtime.harness is None:
        from agent.tools.harness.context import SessionContext
        from agent.tools.harness.harness import ToolHarness
        from agent.tools.bootstrap import build_registry

        runtime.harness = ToolHarness(registry=build_registry())
        runtime.session_ctx = SessionContext()
        logger.info(
            "ToolHarness initialized with %d tools (commerce + admin)",
            len(runtime.harness.registry.tool_names),
        )

    # ── Initialize LLM adapter ──
    if runtime and runtime.llm_adapter is None:
        runtime.llm_adapter = get_llm_adapter()
        logger.info("LLM adapter initialized via get_llm_adapter()")

    # ── Build DAG ──
    graph = StateGraph(PlanState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("product_discovery", product_discovery_node)
    graph.add_node("order_assistant", order_assistant_node)
    graph.add_node("customer_service", customer_service_node)
    graph.add_node("marketing_engine", marketing_engine_node)
    graph.add_node("knowledge_qa", knowledge_qa_node)
    graph.add_node("admin_analyst", admin_analyst_node)
    graph.add_node("tools", tool_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("compliance_check", compliance_node)

    # Entry
    graph.set_entry_point("supervisor")

    # Supervisor -> conditional routing to specialist
    graph.add_conditional_edges(
        "supervisor",
        route_by_intent,
        {
            "product_discovery": "product_discovery",
            "order_assistant": "order_assistant",
            "customer_service": "customer_service",
            "marketing_engine": "marketing_engine",
            "knowledge_qa": "knowledge_qa",
            "admin_analyst": "admin_analyst",
        },
    )

    # Each specialist -> tools or synthesize
    for specialist in _SPECIALISTS:
        graph.add_conditional_edges(
            specialist,
            route_after_specialist,
            {
                "tools": "tools",
                "synthesize": "synthesize",
            },
        )

    # Tools -> back to specialist
    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "product_discovery": "product_discovery",
            "order_assistant": "order_assistant",
            "customer_service": "customer_service",
            "marketing_engine": "marketing_engine",
            "knowledge_qa": "knowledge_qa",
            "admin_analyst": "admin_analyst",
        },
    )

    # Synthesize -> compliance -> END
    graph.add_edge("synthesize", "compliance_check")
    graph.add_edge("compliance_check", END)

    # ── Checkpointer ──
    # 注意: SnapTrip 规划系统已占用 checkpoints 表名, 与 langgraph PostgresSaver 冲突。
    # 同时 langgraph-checkpoint-postgres 3.x API 使用 context manager 模式，
    # 无法在 build_graph 外部保持连接。当前使用 MemorySaver。
    checkpointer: Any = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
