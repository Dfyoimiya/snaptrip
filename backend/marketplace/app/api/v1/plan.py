"""Plan API —— Supervisor + ReAct 架构接口。

端点:
  POST /api/v1/plan/create      —— 提交计划 → Celery 异步执行 → 202
  POST /api/v1/plan/{plan_id}/confirm —— HITL 确认 → Celery 恢复 → 202
  GET  /api/v1/plan/{plan_id}   —— 获取计划状态
  GET  /api/v1/plan/{plan_id}/status —— 查询 plan_run 状态
  GET  /api/v1/plan/{plan_id}/stream —— SSE 流式推送

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid

from agent.adapters.persistence.plan_run import SQLPlanRunRepository
from agent.adapters.persistence.runtime_event import SQLRuntimeEventRepository
from agent.services.agent import AgentService
from agent.tasks.plan_tasks import confirm_plan as celery_confirm
from agent.tasks.plan_tasks import submit_plan as celery_submit
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from snaptrip_shared.core.response import APIServiceError, success
from snaptrip_shared.db.redis import get_redis_client
from snaptrip_shared.schemas.plan import PlanCreateRequest, PlanResponse

from marketplace.app.api.v1.session import stream_plan

router = APIRouter(prefix="/api/v1/plan", tags=["plan"])


class ConfirmRequest(BaseModel):
    decision: str = "confirmed"  # "confirmed" | "modified" | "rejected"
    modified_slots: list[int] = []  # 用户想修改的 slot 序号
    modification_instructions: str = ""


def _build_initial_state(req: PlanCreateRequest) -> dict:
    """构造 PlanState 初始 dict。"""
    plan_id = str(uuid.uuid4())[:8]
    return {
        "plan_id": plan_id,
        "user_id": req.user_id,
        "status": "running",
        "messages": [{"role": "user", "content": req.user_input}],
        "lat": req.lat,
        "lng": req.lng,
    }


def _get_agent_service(request: Request) -> AgentService:
    """获取或构建 AgentService。

    优先使用 lifespan 中已构建的 plan_graph (带 Runtime)，
    否则使用 fallback 空 Runtime。
    """
    if not hasattr(request.app.state, "_agent_service") or request.app.state._agent_service is None:
        if hasattr(request.app.state, "plan_graph") and request.app.state.plan_graph is not None:
            request.app.state._agent_service = AgentService(request.app.state.plan_graph)
        else:
            # Fallback: 使用 MemorySaver 的 graph 构建（同步）
            from agent.graph import build_graph as _sync_build
            import asyncio

            request.app.state._agent_service = AgentService(asyncio.get_event_loop().run_until_complete(_sync_build()))
    return request.app.state._agent_service


@router.post("/create")
async def create_plan(req: PlanCreateRequest, request: Request):
    initial_state = _build_initial_state(req)
    plan_id = initial_state["plan_id"]

    # 写入 plan_run 审计记录
    repo = SQLPlanRunRepository()
    await repo.insert_run(
        run_id=plan_id,
        plan_id=plan_id,
        thread_id=plan_id,
        graph_version="llm-react-v1",
        request_payload=req.model_dump(mode="json"),
        final_status="queued",
    )

    celery_submit.delay(initial_state, plan_id)

    return JSONResponse(
        content=success(data={"plan_id": plan_id, "status": "queued"}),
        status_code=202,
    )


@router.post("/{plan_id}/confirm")
async def confirm_plan(plan_id: str, body: ConfirmRequest, request: Request):
    # Use SQLPlanRunRepository (shared DB) instead of AgentService.get_state()
    # which checks LangGraph checkpoint (MemorySaver, not shared across processes).
    repo = SQLPlanRunRepository()
    run = await repo.get_by_plan_id(plan_id)
    if run is None:
        raise APIServiceError(code=1001, message="plan run not found", status_code=404)

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

    # 返回可用字段
    return success(
        data={
            "plan_id": state.get("plan_id"),
            "status": state.get("status"),
            "scene": state.get("scene"),
            "intent": state.get("intent"),
            "itinerary": state.get("itinerary"),
            "bookings": state.get("bookings"),
            "activity_candidates": state.get("scored_activities"),
            "restaurant_candidates": state.get("scored_restaurants"),
        }
    )


@router.get("/{plan_id}/status")
async def get_plan_status(plan_id: str, request: Request):
    repo = SQLPlanRunRepository()
    run = await repo.get_by_plan_id(plan_id)
    if run is None:
        raise APIServiceError(code=1001, message="plan run not found", status_code=404)
    return success(data=run)


@router.get("/{plan_id}/stream")
async def plan_stream(plan_id: str, request: Request):
    # Check plan run exists in DB (created synchronously in create_plan).
    # Don't check LangGraph checkpoint — the Celery worker may not have
    # started the graph yet. SSE only needs Redis Pub/Sub + event_repo.
    repo = SQLPlanRunRepository()
    run = await repo.get_by_plan_id(plan_id)
    if run is None:
        raise APIServiceError(code=1001, message="plan run not found", status_code=404)
    redis_client = await get_redis_client()
    event_repo = SQLRuntimeEventRepository()
    return await stream_plan(plan_id, redis_client, event_repo, request)
