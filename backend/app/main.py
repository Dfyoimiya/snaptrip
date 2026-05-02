"""SnapTrip MVP —— FastAPI 入口"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.schemas.plan import PlanCreateRequest, PlanResponse
from app.services.plan_service import create_plan

app = FastAPI(
    title="SnapTrip MVP",
    description="本地生活智能规划 —— 最小可行性验证",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PLAN_STORE: dict[str, PlanResponse] = {}


@app.post("/api/v1/plan/create", response_model=PlanResponse)
async def api_create_plan(request: PlanCreateRequest):
    """创建活动计划"""
    plan = await create_plan(request)
    PLAN_STORE[plan.plan_id] = plan
    return plan


@app.get("/api/v1/plan/{plan_id}", response_model=PlanResponse)
async def api_get_plan(plan_id: str):
    plan = PLAN_STORE.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    return plan


@app.get("/api/v1/plan/{plan_id}/stream")
async def api_plan_stream(plan_id: str):
    """SSE 流式返回 Agent 思考过程"""
    plan = PLAN_STORE.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")

    async def event_stream() -> AsyncGenerator[dict, None]:
        events = [
            {"event": "intent", "data": json.dumps({"status": "parsing", "query": plan.query_text}, ensure_ascii=False)},
            {"event": "intent", "data": json.dumps({"status": "done", "constraints": {"guest_count": 2}, "confidence": 0.85}, ensure_ascii=False)},
            {"event": "retrieval", "data": json.dumps({"poi_count": 15, "types": {"attraction": 5, "restaurant": 5, "cafe": 2, "activity": 3}}, ensure_ascii=False)},
            {"event": "planning", "data": json.dumps({"phase": "hard_filter", "candidates": len(plan.slots)}, ensure_ascii=False)},
            {"event": "planning_done", "data": json.dumps({"total_cost": plan.total_cost, "slot_count": len(plan.slots)}, ensure_ascii=False)},
        ]
        for evt in events:
            yield evt
            await asyncio.sleep(0.3)

        for i, slot in enumerate(plan.slots):
            yield {
                "event": "execution",
                "data": json.dumps(
                    {
                        "tool": slot.action,
                        "status": "success",
                        "poi_name": slot.poi.name,
                        "time": slot.time,
                        "cost": slot.estimated_cost,
                    },
                    ensure_ascii=False,
                ),
            }
            await asyncio.sleep(0.3)

        yield {"event": "execution_done", "data": json.dumps({"success_count": len(plan.slots), "failed_count": 0})}
        await asyncio.sleep(0.2)
        yield {"event": "done", "data": json.dumps({"plan_id": plan.plan_id})}

    return EventSourceResponse(event_stream())


@app.get("/health")
async def health():
    return {"status": "ok"}
