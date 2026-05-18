"""Plan API —— 对接 LangGraph 编排引擎。

提供活动计划创建、查询、确认、流式推送的 RESTful 接口。

端点:
  POST /api/v1/plan/create      —— 创建计划，LangGraph StateGraph 驱动全链路
  POST /api/v1/plan/{plan_id}/confirm —— 人机协同：确认/反对计划草案
  GET  /api/v1/plan/{plan_id}   —— 获取已完成计划详情
  GET  /api/v1/plan/{plan_id}/stream —— SSE 流式推送 Agent 思考过程

与旧版差异:
  - 不再硬编码 9 个 Agent 的串行调用
  - 改为 plan_graph.ainvoke() / plan_graph.astream_events()
  - 异常分支 (consensus/execution/fallback) 由 conditional_edges 驱动
  - FSM 状态迁移完全在图内完成
  - consensus_resolver 使用 LangGraph interrupt() 实现人机协同

Author: SnapTrip Team
Date: 2026-05-13 / Refactored 2026-05-17 / Interrupt 2026-05-18
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from langgraph.errors import GraphInterrupt
from langgraph.types import Command
from pydantic import BaseModel

from app.agents.graph import plan_graph
from app.api.v1.session import stream_plan
from app.core.response import APIServiceError, success
from app.schemas.plan import PlanCreateRequest, PlanResponse, PlanSlot, ShareCard

router = APIRouter(prefix="/api/v1/plan", tags=["plan"])


class ConfirmRequest(BaseModel):
    decision: str = "confirmed"
    slot_index: int | None = None


def _build_initial_state(req: PlanCreateRequest) -> dict:
    plan_id = str(uuid.uuid4())[:8]
    return {
        "plan_id": plan_id,
        "session_id": str(uuid.uuid4())[:8],
        "user_id": req.user_id,
        "user_input": req.user_input,
        "lat": req.lat,
        "lng": req.lng,
        "status": "idle",
        "fallback_count": 0,
        "errors": [],
    }


def _state_to_response(state: dict, query_text: str) -> PlanResponse:
    draft = state.get("draft", {}) or {}
    slots_raw = draft.get("slots", [])
    slots = [PlanSlot(**s) if isinstance(s, dict) else s for s in slots_raw]
    share_card_data = state.get("share_card", {}) or {}

    return PlanResponse(
        plan_id=state.get("plan_id", ""),
        query_text=query_text,
        status=state.get("status", "idle"),
        total_cost=draft.get("total_cost", 0),
        total_time_min=draft.get("total_time_min", 0),
        slots=slots,
        share_card=ShareCard(**share_card_data) if share_card_data else None,
    )


@router.post("/create")
async def create_plan(req: PlanCreateRequest, request: Request):
    initial_state = _build_initial_state(req)
    config = {"configurable": {"thread_id": initial_state["plan_id"]}}
    try:
        final_state = await plan_graph.ainvoke(initial_state, config)
    except GraphInterrupt:
        state = await plan_graph.aget_state(config)
        if state and state.values:
            return success(data=_state_to_response(state.values, req.user_input).model_dump())
        raise APIServiceError(code=2001, message="graph interrupted but state unavailable", status_code=500) from None
    return success(data=_state_to_response(final_state, req.user_input).model_dump())


@router.post("/{plan_id}/confirm")
async def confirm_plan(plan_id: str, body: ConfirmRequest, request: Request):
    config = {"configurable": {"thread_id": plan_id}}
    state = await plan_graph.aget_state(config)
    if state is None or state.values is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)
    try:
        final_state = await plan_graph.ainvoke(
            Command(resume={"decision": body.decision, "slot_index": body.slot_index}),
            config,
        )
    except GraphInterrupt:
        state = await plan_graph.aget_state(config)
        if state and state.values:
            return success(data=_state_to_response(state.values, "").model_dump())
        raise APIServiceError(code=2001, message="graph interrupted but state unavailable", status_code=500) from None
    return success(data=_state_to_response(final_state, "").model_dump())


@router.get("/{plan_id}")
async def get_plan(plan_id: str, request: Request):
    config = {"configurable": {"thread_id": plan_id}}
    state = await plan_graph.aget_state(config)
    if state is None or state.values is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)
    return success(data=_state_to_response(state.values, "").model_dump())


@router.get("/{plan_id}/stream")
async def plan_stream(plan_id: str, request: Request):
    config = {"configurable": {"thread_id": plan_id}}
    state_snapshot = await plan_graph.aget_state(config)
    if state_snapshot is None or state_snapshot.values is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)
    return await stream_plan(plan_id, state_snapshot.values)
