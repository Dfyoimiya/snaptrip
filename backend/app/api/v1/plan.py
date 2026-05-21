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

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.agent_runtime import GRAPH_VERSION, build_initial_runtime_state
from app.agent_runtime.response_state import state_to_response
from app.api.v1.session import stream_plan
from app.core.response import APIServiceError, success
from app.schemas.plan import PlanCreateRequest, PlanResponse
from app.services.agent_service import AgentService, InterruptError

router = APIRouter(prefix="/api/v1/plan", tags=["plan"])


class ConfirmRequest(BaseModel):
    decision: str = "confirmed"
    slot_index: int | None = None
    locked_slots: list[int] = []
    rejected_slots: list[int] = []
    instruction: str = ""
    replace_only: bool = False
    change_requests: list[dict] = []


def _build_initial_state(req: PlanCreateRequest) -> dict:
    runtime_state = build_initial_runtime_state(req, graph_version=GRAPH_VERSION)
    return {
        "plan_id": runtime_state.request.plan_id,
        "session_id": runtime_state.request.session_id,
        "user_id": runtime_state.request.user_id,
        "user_input": runtime_state.request.user_input,
        "lat": runtime_state.request.lat,
        "lng": runtime_state.request.lng,
        "status": "idle",
        "fallback_count": 0,
        "errors": [],
        "request": runtime_state.request.model_dump(mode="json"),
    }


def _state_to_response(state: dict, query_text: str) -> PlanResponse:
    return state_to_response(state, query_text)


def _get_agent_service(request: Request) -> AgentService:
    if not hasattr(request.app.state, "_agent_service") or request.app.state._agent_service is None:
        from app.agent_runtime import build_plan_graph
        request.app.state._agent_service = AgentService(build_plan_graph())
    return request.app.state._agent_service  # type: ignore[no-any-return]


@router.post("/create")
async def create_plan(req: PlanCreateRequest, request: Request):
    service = _get_agent_service(request)
    initial_state = _build_initial_state(req)
    plan_id = initial_state["plan_id"]
    try:
        final_state = await service.invoke(initial_state, plan_id)
    except InterruptError:
        state = await service.get_state(plan_id)
        if state:
            return success(data=_state_to_response(state, req.user_input).model_dump())
        raise APIServiceError(code=2001, message="graph interrupted but state unavailable", status_code=500) from None
    return success(data=_state_to_response(final_state, req.user_input).model_dump())


@router.post("/{plan_id}/confirm")
async def confirm_plan(plan_id: str, body: ConfirmRequest, request: Request):
    service = _get_agent_service(request)
    state = await service.get_state(plan_id)
    if state is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)
    try:
        final_state = await service.resume(body.model_dump(), plan_id)
    except InterruptError:
        state = await service.get_state(plan_id)
        if state:
            return success(data=_state_to_response(state, "").model_dump())
        raise APIServiceError(code=2001, message="graph interrupted but state unavailable", status_code=500) from None
    return success(data=_state_to_response(final_state, "").model_dump())


@router.get("/{plan_id}")
async def get_plan(plan_id: str, request: Request):
    service = _get_agent_service(request)
    state = await service.get_state(plan_id)
    if state is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)
    return success(data=_state_to_response(state, "").model_dump())


@router.get("/{plan_id}/stream")
async def plan_stream(plan_id: str, request: Request):
    service = _get_agent_service(request)
    state = await service.get_state(plan_id)
    if state is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)
    return await stream_plan(plan_id, request.app.state.runtime_events)
