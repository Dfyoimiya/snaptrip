"""计划相关 Celery 异步任务。

Supervisor + ReAct 架构:
  - submit_plan: 首次提交 → 运行 graph 直到 present_plan (HITL interrupt)
  - confirm_plan: 用户确认后 → resume graph → executor → send_message → END

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agent.adapters.persistence.plan_run import SQLPlanRunRepository
from agent.adapters.persistence.runtime_event import SQLRuntimeEventRepository
from agent.events.redis_bus import RedisEventBus
from agent.graph import build_graph
from agent.runtime import AgentRuntime
from agent.services.agent import AgentService, InterruptError
from marketplace.app.celery_app import celery_app

logger = logging.getLogger(__name__)

_worker_agent_service: AgentService | None = None

# Persistent event loop for solo Celery pool.
# asyncio.run() creates a new loop each call, which breaks
# SQLAlchemy's async engine connection pool (bound to the first loop).
_loop: asyncio.AbstractEventLoop | None = None


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


async def _build_worker_agent_service() -> AgentService:
    """构建 AgentService（图 + Redis 事件总线 + 高德工具适配器）。"""
    from snaptrip_shared.db.redis import get_redis_pool
    from agent.adapters.amap_adapter import AmapAdapter

    event_bus = RedisEventBus(
        pool=get_redis_pool(),
        repository=SQLRuntimeEventRepository(),
    )
    tool_adapter = AmapAdapter()
    runtime = AgentRuntime(event_bus=event_bus, tool_adapter=tool_adapter)
    graph = await build_graph(runtime=runtime)
    return AgentService(graph)


async def _get_worker_agent_service() -> AgentService:
    global _worker_agent_service
    if _worker_agent_service is None:
        _worker_agent_service = await _build_worker_agent_service()
    return _worker_agent_service


async def _async_submit_plan(initial_state: dict, plan_id: str, task_id: str) -> dict:
    repo = SQLPlanRunRepository()
    await repo.update_status(plan_id, "running")
    service = await _get_worker_agent_service()
    try:
        final_state = await service.invoke(initial_state, plan_id)
    except InterruptError:
        await repo.update_status(plan_id, "awaiting_confirmation")
        return {"status": "awaiting_confirmation", "plan_id": plan_id, "task_id": task_id}
    except Exception as exc:
        await repo.update_status(plan_id, "failed", error_message=str(exc))
        raise
    await repo.update_status(plan_id, "completed")
    return {"status": "completed", "plan_id": plan_id, "task_id": task_id}


async def _async_confirm_plan(resume_data: dict, plan_id: str, task_id: str) -> dict:
    repo = SQLPlanRunRepository()
    await repo.update_status(plan_id, "running")
    service = await _get_worker_agent_service()
    try:
        final_state = await service.resume(resume_data, plan_id)
    except InterruptError:
        await repo.update_status(plan_id, "awaiting_confirmation")
        return {"status": "awaiting_confirmation", "plan_id": plan_id, "task_id": task_id}
    except Exception as exc:
        await repo.update_status(plan_id, "failed", error_message=str(exc))
        raise
    await repo.update_status(plan_id, "completed")
    return {"status": "completed", "plan_id": plan_id, "task_id": task_id}


@celery_app.task(bind=True, name="plan.submit")
def submit_plan(self, initial_state: dict, plan_id: str) -> dict:
    loop = _get_or_create_loop()
    return loop.run_until_complete(_async_submit_plan(initial_state, plan_id, self.request.id))


@celery_app.task(bind=True, name="plan.confirm")
def confirm_plan(self, resume_data: dict, plan_id: str) -> dict:
    loop = _get_or_create_loop()
    return loop.run_until_complete(_async_confirm_plan(resume_data, plan_id, self.request.id))
