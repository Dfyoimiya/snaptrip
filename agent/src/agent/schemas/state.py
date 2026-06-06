"""Agent PlanState —— DAG 工作流统一状态。

LangGraph StateGraph 管理全局状态。每个节点是一个独立的工作单元，
节点间通过条件边（conditional edge）控制流转。

对话历史由 messages (add_messages reducer) 自动累积。

Author: SnapTrip Team
Date: 2026-05-31
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class PlanState(TypedDict, total=False):
    # ── 对话历史（add_messages reducer 自动累积）──
    messages: Annotated[list[BaseMessage], add_messages]

    # ── 会话标识 ──
    plan_id: str
    user_id: str
    lat: float | None
    lng: float | None

    # ── Extract 阶段输出（类型安全，Pydantic 模型）──
    extract_result: Any  # ExtractResult — 在 state.py 中避免循环导入，用 Any 标注
    user_profile: dict[str, Any]  # {dietary_tendency, budget_tendency, travel_style, ...}

    # ── 搜索结果（LLM 调用 amap_poi_search 后逐步填充）──
    activity_candidates: list[dict[str, Any]]
    restaurant_candidates: list[dict[str, Any]]

    # ── 求解结果 ──
    pareto_solutions: list[dict[str, Any]]   # Pareto 前沿
    selected_solution: dict[str, Any]        # LLM 语义选择的最优解

    # ── 行程 ──
    itinerary: dict[str, Any]     # {slots: [...], total_cost, total_time, summary}

    # ── 执行 ──
    bookings: list[dict[str, Any]]
    execution_errors: list[dict[str, Any]]

    # ── HITL 负载（由 tool_node 注入，hitl_node 消费）──
    hitl_payload: dict[str, Any] | None

    # ── DAG 路由与状态 ──
    phase: str  # "extract" | "plan" | "execute" | "done"
    status: str  # "running" | "waiting_user" | "done" | "failed"
