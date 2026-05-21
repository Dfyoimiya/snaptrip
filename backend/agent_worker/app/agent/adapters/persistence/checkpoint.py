"""SQL-backed runtime checkpoint repository."""

from __future__ import annotations

from sqlalchemy import select

from agent_worker.app.agent.models.runtime_checkpoint import RuntimeCheckpoint
from agent_worker.app.agent.ports.repositories import CheckpointRepositoryPort
from agent_worker.app.agent.schemas.state import CheckpointSnapshot
from shared.db.session import AsyncSessionLocal


class SQLRuntimeCheckpointRepository(CheckpointRepositoryPort):
    """Best-effort typed checkpoint persistence."""

    async def save(self, checkpoint: CheckpointSnapshot) -> None:
        try:
            async with AsyncSessionLocal() as db:
                db.add(
                    RuntimeCheckpoint(
                        plan_id=checkpoint.draft.plan_id,
                        run_id=checkpoint.draft.plan_id,
                        version=checkpoint.version,
                        state_json=checkpoint.model_dump(mode="json"),
                    )
                )
                await db.commit()
        except Exception:
            return

    async def load_latest(self, plan_id: str) -> CheckpointSnapshot | None:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(RuntimeCheckpoint)
                    .where(RuntimeCheckpoint.plan_id == plan_id)
                    .order_by(RuntimeCheckpoint.created_at.desc())
                    .limit(1)
                )
                row = result.scalar_one_or_none()
        except Exception:
            return None

        if row is None:
            return None
        return CheckpointSnapshot(**row.state_json)
