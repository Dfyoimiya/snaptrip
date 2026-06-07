# ────────────────────────────────────────────────────────────────────────────
# 🔵 FRAMEWORK — Agent DAG Workflow Builder
# ────────────────────────────────────────────────────────────────────────────
# This is the core StateGraph builder. It provides the DI container, node
# registration, conditional routing, and checkpointing infrastructure.
#
# Trip-planning nodes (extract/plan/hitl) have been archived to _archived/.
# Replace the placeholder nodes below with your domain-specific logic.
#
# Archived: 2026-06-07 — repurposed from trip planning agent
# ────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.runtime import AgentRuntime
from agent.schemas.state import PlanState
from agent.tool_node import tool_node
from agent.utils import get_llm_adapter
from snaptrip_shared.core.config import settings

logger = logging.getLogger(__name__)

# ── Global DI ──
_runtime: AgentRuntime | None = None


# ── Placeholder nodes (replace with your domain logic) ─────────────────────


async def _placeholder_node(state: PlanState) -> dict:
    """Placeholder LLM reasoning node.

    Replace this with your own agent node implementation.
    See _archived/agent_node.py and _archived/extract_node.py for reference.
    """
    return {"messages": []}


# ── Conditional routing ────────────────────────────────────────────────────


def route_after_agent(state: PlanState) -> Literal["tools", "end"]:
    """Route after LLM node: tools if tool_calls exist, else end."""
    msgs = state.get("messages", [])
    if not msgs:
        return "end"
    last_msg = msgs[-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    return "tools" if tool_calls else "end"


def route_after_tools(state: PlanState) -> Literal["agent"]:
    """Route after tool execution back to agent node."""
    return "agent"


# ── Graph builder ───────────────────────────────────────────────────────────


async def build_graph(runtime: AgentRuntime | None = None) -> CompiledStateGraph:
    """Build the agent DAG.

    Nodes:
      agent — LLM reasoning node (replace with your domain logic)
      tools — tool execution dispatch

    Args:
        runtime: optional DI container

    Returns:
        CompiledStateGraph with PostgresSaver (or MemorySaver fallback)
    """
    global _runtime
    _runtime = runtime

    # ── Initialize ToolHarness + SessionContext ──
    if runtime and runtime.harness is None:
        from agent.tools.harness.context import SessionContext
        from agent.tools.harness.harness import ToolHarness

        # Replace with your own tool registry builder
        from agent.tools.registry.registry import ToolRegistry
        runtime.harness = ToolHarness(registry=ToolRegistry())
        runtime.session_ctx = SessionContext()
        logger.info("ToolHarness initialized (empty registry — register your tools)")

    # ── Initialize LLM adapter ──
    if runtime and runtime.llm_adapter is None:
        runtime.llm_adapter = get_llm_adapter()
        logger.info("LLM adapter initialized via get_llm_adapter()")

    # ── Build DAG ──
    graph = StateGraph(PlanState)

    graph.add_node("agent", _placeholder_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "end": END},
    )
    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {"agent": "agent"},
    )

    # ── Checkpointer ──
    db_url = settings.DATABASE_URL
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
        await checkpointer.setup()
        logger.info("PostgresSaver initialized for graph checkpointing")
    except Exception:
        logger.warning(
            "PostgresSaver setup failed, falling back to MemorySaver. "
            "Checkpoint state will be lost on restart."
        )
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
