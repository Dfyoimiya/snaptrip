"""RuntimeEvent 持久化适配器。

通过共享 AsyncSessionLocal 操作 plan_run_events 表，
同时写入 Redis 事件总线用于 SSE 推送。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from snaptrip_shared.db.session import AsyncSessionLocal

from pydantic import BaseModel

from agent.schemas.events import RuntimeEvent

logger = logging.getLogger(__name__)


def _get_payload_field(payload: object, field: str, default: Any = "") -> Any:
    """从 payload 中安全提取字段——兼容 dict 和 Pydantic model。"""
    if payload is None:
        return default
    if isinstance(payload, BaseModel):
        return getattr(payload, field, default) or default
    if isinstance(payload, dict):
        return payload.get(field, default)
    return default


class SQLRuntimeEventRepository:
    """RuntimeEvent 数据库 + Redis 持久化适配器。"""

    async def append(self, event: RuntimeEvent) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    """INSERT INTO plan_run_events
                       (id, event_id, run_id, plan_id, node_name, event_type,
                        payload_json)
                       VALUES (:id, :event_id, :run_id, :plan_id, :node_name,
                        :event_type, :payload_json)"""
                ),
                {
                    "id": uuid.uuid4(),
                    "event_id": event.event_id,
                    "run_id": _get_payload_field(event.payload, "run_id"),
                    "plan_id": event.plan_id,
                    "node_name": event.node_name,
                    "event_type": event.event_type,
                    "payload_json": json.dumps(event.model_dump(mode="json"), ensure_ascii=False),
                },
            )
            await session.commit()

    async def list_by_plan(self, plan_id: str) -> list[RuntimeEvent]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    """SELECT event_id, run_id, plan_id, node_name, event_type,
                       payload_json, created_at
                       FROM plan_run_events WHERE plan_id = :plan_id
                       ORDER BY created_at ASC"""
                ),
                {"plan_id": plan_id},
            )
            rows = result.mappings().all()
            events: list[RuntimeEvent] = []
            for row in rows:
                payload = row["payload_json"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if isinstance(payload, dict):
                    events.append(RuntimeEvent(**payload))
                else:
                    events.append(RuntimeEvent(
                        event_id=row["event_id"],
                        plan_id=row["plan_id"],
                        node_name=row["node_name"],
                        event_type=row["event_type"],
                        payload=payload,
                    ))
            return events

    async def get_events_after(self, plan_id: str, event_id: str) -> list[RuntimeEvent]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    """SELECT event_id, run_id, plan_id, node_name, event_type,
                       payload_json, created_at
                       FROM plan_run_events
                       WHERE plan_id = :plan_id AND created_at > (
                         SELECT created_at FROM plan_run_events
                         WHERE event_id = :event_id LIMIT 1
                       )
                       ORDER BY created_at ASC"""
                ),
                {"plan_id": plan_id, "event_id": event_id},
            )
            rows = result.mappings().all()
            events: list[RuntimeEvent] = []
            for row in rows:
                payload = row["payload_json"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if isinstance(payload, dict):
                    events.append(RuntimeEvent(**payload))
                else:
                    events.append(RuntimeEvent(
                        event_id=row["event_id"],
                        plan_id=row["plan_id"],
                        node_name=row["node_name"],
                        event_type=row["event_type"],
                        payload=payload,
                    ))
            return events
