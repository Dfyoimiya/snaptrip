"""Plan API —— 异步计划服务入口（Phase 3a）。

提供活动计划提交、查询、确认、流式推送的 RESTful 接口。

端点:
  POST /api/v1/plan/create      —— 提交计划 → Celery 异步执行 → 202
  POST /api/v1/plan/{plan_id}/confirm —— 人机协同确认 → Celery 异步恢复 → 202
  GET  /api/v1/plan/{plan_id}   —— 获取计划详情（从 checkpoint 读取）
  GET  /api/v1/plan/{plan_id}/status —— 查询 plan_run 执行状态
  GET  /api/v1/plan/{plan_id}/stream —— SSE 流式推送（从 RuntimeEventStore 读取）

Phase 3a 变更:
  - POST /create 和 /confirm 不再同步执行 graph，改为 Celery task 派发
  - 新增 GET /status 查询 plan_runs 状态
  - GET /{plan_id} 和 /stream 仍从 checkpoint/event store 读取（跨进程兼容）

Author: SnapTrip Team
Date: 2026-05-13 / Phase 2 2026-05-21 / Phase 3a 2026-05-21
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from snaptrip_shared.core.response import APIServiceError, success
from snaptrip_shared.db.redis import get_redis_client
from snaptrip_shared.schemas.plan import PlanCreateRequest, PlanResponse

from agent_worker.app.agent.adapters.persistence.plan_run import SQLPlanRunRepository
from agent_worker.app.agent.adapters.persistence.runtime_event import SQLRuntimeEventRepository
from agent_worker.app.agent.services.agent import AgentService
from agent_worker.app.agent.state.builder import GRAPH_VERSION, build_initial_runtime_state
from agent_worker.app.agent.state.response import state_to_response
from agent_worker.app.tasks.plan_tasks import confirm_plan as celery_confirm
from agent_worker.app.tasks.plan_tasks import submit_plan as celery_submit
from marketplace.app.api.v1.session import stream_plan

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
        from agent_worker.app.agent.graph import build_plan_graph

        request.app.state._agent_service = AgentService(build_plan_graph())
    return request.app.state._agent_service  # type: ignore[no-any-return]


@router.post("/create")
async def create_plan(req: PlanCreateRequest, request: Request):
    initial_state = _build_initial_state(req)
    plan_id = initial_state["plan_id"]

    # 写入 plan_run 审计记录（status=queued）
    repo = SQLPlanRunRepository()
    await repo.insert_run(
        run_id=plan_id,
        plan_id=plan_id,
        thread_id=initial_state.get("session_id", plan_id),
        graph_version=GRAPH_VERSION,
        request_payload=req.model_dump(mode="json"),
        final_status="queued",
    )

    # 派发 Celery 异步任务
    celery_submit.delay(initial_state, plan_id)

    return JSONResponse(
        content=success(data={"plan_id": plan_id, "status": "queued"}),
        status_code=202,
    )


@router.post("/{plan_id}/confirm")
async def confirm_plan(plan_id: str, body: ConfirmRequest, request: Request):
    service = _get_agent_service(request)
    state = await service.get_state(plan_id)
    if state is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)

    # 派发 Celery 异步恢复任务
    celery_confirm.delay(body.model_dump(), plan_id)

    return JSONResponse(
        content=success(data={"plan_id": plan_id, "status": "accepted"}),
        status_code=202,
    )


@router.get("/{plan_id}")
async def get_plan(plan_id: str, request: Request):
    service = _get_agent_service(request)
    state = await service.get_state(plan_id)
    if state is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)
    return success(data=_state_to_response(state, "").model_dump())


@router.get("/{plan_id}/status")
async def get_plan_status(plan_id: str, request: Request):
    repo = SQLPlanRunRepository()
    run = await repo.get_by_plan_id(plan_id)
    if run is None:
        raise APIServiceError(code=1001, message="plan run not found", status_code=404)
    return success(data=run)


@router.get("/{plan_id}/stream")
async def plan_stream(plan_id: str, request: Request):
    service = _get_agent_service(request)
    state = await service.get_state(plan_id)
    if state is None:
        raise APIServiceError(code=1001, message="plan not found", status_code=404)
    redis_client = await get_redis_client()
    event_repo = SQLRuntimeEventRepository()
    return await stream_plan(plan_id, redis_client, event_repo, request)
