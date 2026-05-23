"""SQL-backed runtime event repository."""

from __future__ import annotations

from snaptrip_shared.db.session import AsyncSessionLocal
from sqlalchemy import select

from agent.models.plan_run_event import PlanRunEvent
from agent.ports.repositories import RuntimeEventRepositoryPort
from agent.schemas.events import RuntimeEvent


def _row_to_event(row: PlanRunEvent) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=row.event_id,
        run_id=row.run_id,
        plan_id=row.plan_id,
        node_name=row.node_name,
        event_type=row.event_type,
        timestamp=row.created_at,
        payload=row.payload_json or {},
    )


class SQLRuntimeEventRepository(RuntimeEventRepositoryPort):
    """Best-effort runtime event persistence."""

    async def append(self, event: RuntimeEvent) -> None:
        try:
            async with AsyncSessionLocal() as db:
                db.add(
                    PlanRunEvent(
                        event_id=event.event_id,
                        run_id=event.run_id,
                        plan_id=event.plan_id,
                        node_name=event.node_name,
                        event_type=event.event_type,
                        payload_json=event.payload,
                    )
                )
                await db.commit()
        except Exception:
            return

    async def list_by_plan(self, plan_id: str) -> list[RuntimeEvent]:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(PlanRunEvent).where(PlanRunEvent.plan_id == plan_id).order_by(PlanRunEvent.created_at.asc())
                )
                rows = result.scalars().all()
        except Exception:
            return []

        return [_row_to_event(row) for row in rows]

    async def get_events_after(self, plan_id: str, after_timestamp: str) -> list[RuntimeEvent]:
        """返回指定 plan 在 after_timestamp 之后产生的所有事件（用于 SSE 断线重连回放）。"""
        try:
            from datetime import datetime

            after_dt = datetime.fromisoformat(after_timestamp)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(PlanRunEvent)
                    .where(
                        PlanRunEvent.plan_id == plan_id,
                        PlanRunEvent.created_at > after_dt,
                    )
                    .order_by(PlanRunEvent.created_at.asc())
                )
                rows = result.scalars().all()
        except Exception:
            return []

        return [_row_to_event(row) for row in rows]
