# ────────────────────────────────────────────────────────────────────────────
# 🔵 FRAMEWORK — Agent State (PlanState)
# ────────────────────────────────────────────────────────────────────────────
# Unified TypedDict for LangGraph StateGraph.
#
# Trip-specific fields (extract_result, candidates, pareto_solutions, solvers,
# itinerary, bookings) have been removed.
# Add your domain-specific fields below.
#
# Archived: 2026-06-07 — repurposed from trip planning agent
# ────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class PlanState(TypedDict, total=False):
    # ── Conversation history (auto-accumulated via add_messages reducer) ──
    messages: Annotated[list[BaseMessage], add_messages]

    # ── Session identity ──
    plan_id: str
    user_id: str

    # ── HITL payload (set by tool_node, consumed by hitl_node) ──
    hitl_payload: dict[str, Any] | None

    # ── DAG routing & status ──
    phase: str   # domain-specific phase name
    status: str  # "running" | "waiting_user" | "done" | "failed"
