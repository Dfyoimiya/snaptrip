"""SQL-backed runtime event repository."""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.plan_run_event import PlanRunEvent
from app.ports.repositories import RuntimeEventRepositoryPort
from app.schemas.agent.events import RuntimeEvent


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

        return [
            RuntimeEvent(
                event_id=row.event_id,
                run_id=row.run_id,
                plan_id=row.plan_id,
                node_name=row.node_name,
                event_type=row.event_type,
                timestamp=row.created_at,
                payload=row.payload_json or {},
            )
            for row in rows
        ]
