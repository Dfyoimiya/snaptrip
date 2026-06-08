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
    session_id: str

    # ── Intent routing ──
    intent: str  # "product_search" | "order_status" | "coupon_inquiry" | "general"
    intent_confidence: float
    current_agent: str  # which specialist is active

    # ── Domain results ──
    sub_results: dict[str, Any]  # keyed by agent name
    product_results: list[dict[str, Any]]
    order_detail: dict[str, Any] | None

    # ── Memory ──
    working_memory: dict[str, Any]  # scratchpad for multi-step reasoning
    retry_count: int

    # ── HITL payload (set by tool_node, consumed by hitl_node) ──
    hitl_payload: dict[str, Any] | None

    # ── DAG routing & status ──
    phase: str  # domain-specific phase name
    status: str  # "running" | "waiting_user" | "done" | "failed"
