"""SSE 流式输出 —— 跨进程 Redis Pub/Sub。

Agent Worker 通过 Redis PUBLISH 发射事件，Gateway 通过 SUBSCRIBE 接收。

流程:
  1. Last-Event-ID 存在 → DB 回放缺失事件（断线重连）
  2. SUBSCRIBE Redis plan:{plan_id}:events
  3. 终端事件 (plan_completed) → 自动关闭 SSE

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import suppress

from agent.ports.repositories import RuntimeEventRepositoryPort
from agent.schemas.events import RuntimeEvent
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

EVENT_NAME_MAP: dict[tuple[str, str], str] = {
    # Supervisor
    ("parse_intent", "node_started"): "intent",
    ("parse_intent", "node_succeeded"): "intent_done",
    ("plan_tasks", "node_started"): "planning",
    ("plan_tasks", "node_succeeded"): "planning_done",
    # Sub-Agents (parallel)
    ("activity_search_react", "node_started"): "searching_activities",
    ("activity_search_react", "node_succeeded"): "activities_found",
    ("restaurant_search_react", "node_started"): "searching_restaurants",
    ("restaurant_search_react", "node_succeeded"): "restaurants_found",
    ("constraint_validator", "node_started"): "validating",
    ("constraint_validator", "node_succeeded"): "validation_done",
    # Scoring & Composition
    ("score_and_rank", "node_started"): "scoring",
    ("score_and_rank", "node_succeeded"): "scoring_done",
    ("compose_itinerary", "node_started"): "composing",
    ("compose_itinerary", "node_succeeded"): "itinerary_ready",
    # HITL
    ("present_plan", "interrupt_requested"): "need_confirmation",
    # Execution
    ("executor", "node_started"): "executing",
    ("executor", "node_succeeded"): "execution_done",
    ("executor", "node_failed"): "execution_failed",
    ("send_message", "node_succeeded"): "notified",
    # Terminal
    ("plan", "plan_completed"): "done",
}


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def _event_to_sse(event: RuntimeEvent) -> dict:
    event_name = EVENT_NAME_MAP.get((event.node_name, event.event_type), event.event_type)

    # Serialize payload — Pydantic models (UserMessagePayload) have model_dump(),
    # dict payloads are spread directly
    raw_payload = event.payload
    if raw_payload is None:
        payload_data: dict = {}
    elif isinstance(raw_payload, BaseModel):
        payload_data = raw_payload.model_dump()
    else:
        payload_data = raw_payload

    sse_payload = {"plan_id": event.plan_id, "node": event.node_name, **payload_data}
    return _sse(event_name, sse_payload)


async def _event_generator(
    plan_id: str,
    redis_client,  # redis.asyncio.Redis
    event_repo: RuntimeEventRepositoryPort,
    last_event_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """跨进程 SSE 事件生成器。

    1. DB 回放（断线重连）
    2. Redis Pub/Sub 实时订阅
    3. 终端事件自动退出
    """
    # DB 回放
    if last_event_id is not None:
        try:
            replayed = await event_repo.get_events_after(plan_id, last_event_id)
        except Exception:
            replayed = []
        for event in replayed:
            yield _event_to_sse(event)
            if event.event_type == "plan_completed":
                return
    else:
        try:
            initial_events = await event_repo.list_by_plan(plan_id)
        except Exception:
            initial_events = []
        for event in initial_events:
            yield _event_to_sse(event)
            if event.event_type == "plan_completed":
                return

    # Redis Pub/Sub 实时订阅
    channel = f"plan:{plan_id}:events"
    pubsub = redis_client.pubsub()
    try:
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                event = RuntimeEvent.model_validate_json(message["data"])
            except Exception:
                continue
            yield _event_to_sse(event)
            if event.event_type == "plan_completed":
                break
    finally:
        with suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.close()


async def stream_plan(
    plan_id: str,
    redis_client,  # redis.asyncio.Redis
    event_repo: RuntimeEventRepositoryPort,
    request,  # fastapi.Request
) -> EventSourceResponse:
    """跨进程 SSE 端点入口。"""
    last_event_id = request.headers.get("Last-Event-ID") or None
    return EventSourceResponse(_event_generator(plan_id, redis_client, event_repo, last_event_id))
