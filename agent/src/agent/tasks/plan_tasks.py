"""计划相关 Celery 异步任务。

Phase 3a: 从 stub 升级为真实图执行——通过 AgentService 在 Worker 进程内
异步运行 LangGraph + Agent 链路。

Author: SnapTrip Team
Date: 2026-05-17 / Phase 3a refactor 2026-05-21
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agent.adapters.mock_gateway import MockAPIGateway
from agent.adapters.persistence.plan_run import SQLPlanRunRepository
from agent.adapters.persistence.runtime_event import SQLRuntimeEventRepository
from agent.events.redis_bus import RedisEventBus
from agent.graph import build_plan_graph
from agent.runtime import AgentRuntime
from agent.services.agent import AgentService, InterruptError
from marketplace.app.celery_app import celery_app

logger = logging.getLogger(__name__)

_worker_agent_service: AgentService | None = None


def _build_worker_agent_service() -> AgentService:
    """在 Worker 进程内构建 AgentService（含图 + 依赖）。

    Phase 3b: 使用 RedisEventBus 替代 in-memory RuntimeEventStore，
    事件通过 Redis PUBLISH 跨进程推送到 Gateway SSE。
    RedisEventBus 接受 ConnectionPool（lazy client），避免跨 asyncio.run() 的 event loop 绑定。

    gateway.start() 不在此时调用 —— MockAPIGateway.call() 内部有 lazy init，
    会在首次 call() 时于正确的 event loop 中创建 httpx.AsyncClient。
    """
    from snaptrip_shared.db.redis import get_redis_pool

    gateway = MockAPIGateway()

    event_bus = RedisEventBus(
        pool=get_redis_pool(),
        repository=SQLRuntimeEventRepository(),
    )
    runtime = AgentRuntime(gateway=gateway, event_sink=event_bus)
    graph = build_plan_graph(runtime=runtime)
    return AgentService(graph)


def _get_worker_agent_service() -> AgentService:
    """模块级懒加载——每个 Worker 进程只构建一次图。"""
    global _worker_agent_service
    if _worker_agent_service is None:
        _worker_agent_service = _build_worker_agent_service()
    return _worker_agent_service


async def _async_submit_plan(initial_state: dict, plan_id: str, task_id: str) -> dict:
    """所有异步操作在单一 event loop 内完成。

    将 graph 执行 + DB 状态更新放在同一个 asyncio.run() 中，
    避免多个 event loop 之间的 SQLAlchemy/httpx 连接冲突。
    """
    repo = SQLPlanRunRepository()
    await repo.update_status(plan_id, "running")
    service = _get_worker_agent_service()
    try:
        final_state = await service.invoke(initial_state, plan_id)
    except InterruptError:
        await repo.update_status(plan_id, "awaiting_confirmation")
        return {
            "status": "awaiting_confirmation",
            "plan_id": plan_id,
            "task_id": task_id,
        }
    except Exception as exc:
        await repo.update_status(plan_id, "failed", error_message=str(exc))
        raise
    await repo.update_status(plan_id, "completed")
    result: dict[Any, Any] = final_state
    return result


async def _async_confirm_plan(resume_data: dict, plan_id: str, task_id: str) -> dict:
    """confirm_plan 的 async 实现 —— 所有操作在单一 event loop 内完成。"""
    repo = SQLPlanRunRepository()
    await repo.update_status(plan_id, "running")
    service = _get_worker_agent_service()
    try:
        final_state = await service.resume(resume_data, plan_id)
    except InterruptError:
        await repo.update_status(plan_id, "awaiting_confirmation")
        return {
            "status": "awaiting_confirmation",
            "plan_id": plan_id,
            "task_id": task_id,
        }
    except Exception as exc:
        await repo.update_status(plan_id, "failed", error_message=str(exc))
        raise
    await repo.update_status(plan_id, "completed")
    result: dict[Any, Any] = final_state
    return result


# ====================================================================
# 新任务 —— 异步图执行（Phase 3a）
# ====================================================================


@celery_app.task(bind=True, name="plan.submit")
def submit_plan(self, initial_state: dict, plan_id: str) -> dict:
    """提交计划到 Agent 图异步执行。

    Worker 进程调用 AgentService.invoke() 运行全链路 Agent。
    InterruptError 视为正常状态（人机协同等待确认）。
    """
    return asyncio.run(_async_submit_plan(initial_state, plan_id, self.request.id))


@celery_app.task(bind=True, name="plan.confirm")
def confirm_plan(self, resume_data: dict, plan_id: str) -> dict:
    """从中断点恢复图执行（人机协同确认）。"""
    return asyncio.run(_async_confirm_plan(resume_data, plan_id, self.request.id))


# ====================================================================
# 旧任务 —— 保留向后兼容（stub）
# ====================================================================


@celery_app.task(bind=True, name="plan.create_async")
def create_plan_async(
    self, user_input: str, user_id: str, lat: float, lng: float
) -> dict:
    """[deprecated] 使用 submit_plan 替代。"""
    return {
        "task_id": self.request.id,
        "status": "queued",
        "user_input": user_input,
        "user_id": user_id,
    }


@celery_app.task(bind=True, name="plan.notify_share")
def notify_share_card(self, plan_id: str, user_id: str) -> dict:
    """异步生成分享卡片"""
    return {
        "task_id": self.request.id,
        "plan_id": plan_id,
        "user_id": user_id,
        "status": "queued",
    }


@celery_app.task(bind=True, name="user.rebuild_preference_embedding")
def rebuild_user_preference_embedding(self, user_id: str) -> dict:
    """异步重建用户偏好向量"""
    return {
        "task_id": self.request.id,
        "user_id": user_id,
        "status": "queued",
        "message": "偏好向量重建任务已入队",
    }
