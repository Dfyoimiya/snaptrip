"""SQL-backed plan run repository."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.plan_run import PlanRun


class SQLPlanRunRepository:
    """Best-effort plan run audit persistence."""

    async def insert_run(
        self,
        *,
        run_id: str,
        plan_id: str,
        thread_id: str,
        graph_version: str,
        request_payload: dict,
        final_status: str,
        seed: int,
        debug: bool,
        error_message: str | None = None,
    ) -> None:
        try:
            async with AsyncSessionLocal() as db:
                db.add(
                    PlanRun(
                        run_id=run_id,
                        plan_id=plan_id,
                        thread_id=thread_id,
                        graph_version=graph_version,
                        request_payload=request_payload,
                        final_status=final_status,
                        seed=seed,
                        debug=debug,
                        error_message=error_message,
                    )
                )
                await db.commit()
        except Exception:
            return
