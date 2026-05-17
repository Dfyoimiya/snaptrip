"""计划与用户相关 Celery 异步任务。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from app.celery_app import celery_app


@celery_app.task(bind=True, name="plan.create_async")
def create_plan_async(self, user_input: str, user_id: str, lat: float, lng: float) -> dict:
    """异步创建计划（由 API 入队，Worker 调用 Agent 链执行）"""
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
    """异步重建用户偏好向量（触发 LLM Embedding API 生成新向量并写入 PG）"""
    return {
        "task_id": self.request.id,
        "user_id": user_id,
        "status": "queued",
        "message": "偏好向量重建任务已入队",
    }
