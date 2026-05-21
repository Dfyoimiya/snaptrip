"""SQL-backed plan run repository."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.plan_run import PlanRun

logger = logging.getLogger(__name__)


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
        seed: int = 0,
        debug: bool = False,
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

    async def update_status(
        self,
        plan_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """更新 plan_run 状态（按 plan_id 查找最新记录）。"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(PlanRun).where(PlanRun.plan_id == plan_id).order_by(PlanRun.created_at.desc()).limit(1)
                )
                run = result.scalar_one_or_none()
                if run is not None:
                    run.final_status = status
                    if error_message is not None:
                        run.error_message = error_message
                    await db.commit()
        except Exception:
            logger.warning("plan_run_update_failed plan_id=%s", plan_id, exc_info=True)

    async def get_by_plan_id(self, plan_id: str) -> dict | None:
        """按 plan_id 查询最新 plan_run 记录。"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(PlanRun).where(PlanRun.plan_id == plan_id).order_by(PlanRun.created_at.desc()).limit(1)
                )
                run = result.scalar_one_or_none()
                if run is None:
                    return None
                return {
                    "plan_id": run.plan_id,
                    "status": run.final_status,
                    "error_message": run.error_message,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                }
        except Exception:
            logger.warning("plan_run_get_failed plan_id=%s", plan_id, exc_info=True)
            return None
