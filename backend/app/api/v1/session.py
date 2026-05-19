"""SSE 流式输出 —— 订阅真实 runtime event 流。

通过 Server-Sent Events 将 runtime event store 中的真实事件推送到前端。

Author: SnapTrip Team
Date: 2026-05-13 / Refactored 2026-05-17
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from sse_starlette.sse import EventSourceResponse

from app.agent_runtime.event_store import RuntimeEventStore
from app.schemas.agent.events import RuntimeEvent

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
}


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def _event_to_sse(event: RuntimeEvent) -> dict:
    event_name = EVENT_NAME_MAP.get((event.node_name, event.event_type), event.event_type)
    payload = {"plan_id": event.plan_id, "node": event.node_name, **(event.payload or {})}
    return _sse(event_name, payload)


async def stream_plan(plan_id: str, event_store: RuntimeEventStore):
    async def event_generator() -> AsyncGenerator[dict, None]:
        index = 0
        initial_events = await event_store.list_by_plan(plan_id)
        for event in initial_events:
            index += 1
            yield _event_to_sse(event)
            if event.event_type == "plan_completed":
                return

        while True:
            new_events = await event_store.wait_for_events(plan_id, index, timeout_s=10.0)
            if not new_events:
                yield _sse("heartbeat", {"plan_id": plan_id})
                continue
            for event in new_events:
                index += 1
                yield _event_to_sse(event)
                if event.event_type == "plan_completed":
                    return

    return EventSourceResponse(event_generator())
