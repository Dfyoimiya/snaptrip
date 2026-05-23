"""SSE 流式输出 —— 跨进程 Redis Pub/Sub。

Phase 3b: 不再依赖同进程 in-memory RuntimeEventStore。
Agent Worker 通过 Redis PUBLISH 发射事件，Gateway 通过 SUBSCRIBE 接收。

流程:
  1. Last-Event-ID 存在 → 从 plan_run_events 表回放缺失事件（断线重连）
  2. 回放完毕 → SUBSCRIBE Redis plan:{plan_id}:events
  3. 收到终端事件 (plan_completed) → 自动关闭 SSE

Author: SnapTrip Team
Date: 2026-05-13 / Phase 3b refactor 2026-05-22
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import suppress

from agent.ports.repositories import RuntimeEventRepositoryPort
from agent.schemas.events import RuntimeEvent
from sse_starlette.sse import EventSourceResponse

EVENT_NAME_MAP: dict[tuple[str, str], str] = {
    ("intent_parser", "node_started"): "intent",
    ("retrieval_engine", "node_started"): "retrieval",
    ("planning_engine", "node_started"): "planning",
    ("planning_engine", "node_succeeded"): "planning_done",
    ("execution_engine", "node_started"): "execution",
    ("execution_engine", "node_succeeded"): "execution_done",
    ("fallback_engine", "node_started"): "fallback",
    ("consensus_resolver", "interrupt_requested"): "consensus",
    ("notify_engine", "node_started"): "notify",
    ("plan", "plan_completed"): "done",
    # ── 单 Agent 模式 ──
    ("planner", "node_started"): "intent",
    ("planner", "node_succeeded"): "planning_done",
    ("execution", "node_started"): "execution",
    ("execution", "node_succeeded"): "execution_done",
    ("fallback", "node_started"): "fallback",
    ("consensus", "interrupt_requested"): "consensus",
    ("notify", "node_started"): "notify",
}


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def _event_to_sse(event: RuntimeEvent) -> dict:
    event_name = EVENT_NAME_MAP.get((event.node_name, event.event_type), event.event_type)
    payload = {"plan_id": event.plan_id, "node": event.node_name, **(event.payload or {})}
    return _sse(event_name, payload)


async def _event_generator(
    plan_id: str,
    redis_client,  # redis.asyncio.Redis
    event_repo: RuntimeEventRepositoryPort,
    last_event_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """跨进程 SSE 事件生成器。

    1. DB 回放（断线重连）
    2. Redis Pub/Sub 订阅实时事件
    3. 终端事件自动退出
    """
    # ── Phase 1: DB 回放（支持 Last-Event-ID 断线重连）──
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
        # 首次连接 — 回放全部已持久化事件
        try:
            initial_events = await event_repo.list_by_plan(plan_id)
        except Exception:
            initial_events = []
        for event in initial_events:
            yield _event_to_sse(event)
            if event.event_type == "plan_completed":
                return

    # ── Phase 2: Redis Pub/Sub 实时订阅 ──
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


async def stream_plan(
    plan_id: str,
    redis_client,  # redis.asyncio.Redis
    event_repo: RuntimeEventRepositoryPort,
    request,  # fastapi.Request (for Last-Event-ID header)
) -> EventSourceResponse:
    """跨进程 SSE 端点入口。

    Args:
        plan_id: 计划 ID
        redis_client: Redis 异步客户端（从连接池获取）
        event_repo: 运行时事件持久化仓库
        request: FastAPI Request（读取 Last-Event-ID header）
    """
    last_event_id = request.headers.get("Last-Event-ID") or None
    return EventSourceResponse(_event_generator(plan_id, redis_client, event_repo, last_event_id))
