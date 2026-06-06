"""PlanRun 持久化适配器。

通过共享 AsyncSessionLocal 操作 plan_runs 表。

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

logger = logging.getLogger(__name__)


class SQLPlanRunRepository:
    """PlanRun 数据库操作适配器。"""

    async def insert_run(
        self,
        run_id: str,
        plan_id: str,
        thread_id: str,
        graph_version: str,
        request_payload: dict[str, Any],
        final_status: str = "queued",
        seed: int = 0,
        debug: bool = False,
    ) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    """INSERT INTO plan_runs (id, run_id, plan_id, thread_id,
                       graph_version, request_payload, final_status, seed, debug)
                       VALUES (:id, :run_id, :plan_id, :thread_id,
                       :graph_version, :request_payload, :final_status,
                       :seed, :debug)"""
                ),
                {
                    "id": uuid.uuid4(),
                    "run_id": run_id,
                    "plan_id": plan_id,
                    "thread_id": thread_id,
                    "graph_version": graph_version,
                    "request_payload": json.dumps(request_payload, ensure_ascii=False),
                    "final_status": final_status,
                    "seed": seed,
                    "debug": debug,
                },
            )
            await session.commit()

    async def update_status(
        self, plan_id: str, status: str, error_message: str = ""
    ) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    """UPDATE plan_runs SET final_status = :status,
                       error_message = :error_message
                       WHERE plan_id = :plan_id"""
                ),
                {
                    "status": status,
                    "error_message": error_message or None,
                    "plan_id": plan_id,
                },
            )
            await session.commit()

    async def get_by_plan_id(self, plan_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    """SELECT run_id, plan_id, thread_id, graph_version,
                       request_payload, final_status, seed, debug, error_message,
                       created_at
                       FROM plan_runs WHERE plan_id = :plan_id
                       ORDER BY created_at DESC LIMIT 1"""
                ),
                {"plan_id": plan_id},
            )
            row = result.mappings().first()
            if row is None:
                return None
            return dict(row)
