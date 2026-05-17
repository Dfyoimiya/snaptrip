"""用户服务 —— 偏好向量触发与辅助逻辑。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations


def trigger_preference_embedding_update(user_id: str) -> str | None:
    """异步触发偏好向量重建。

    如果 Celery 可用，入队任务；否则返回 None（Worker 未启动时优雅降级）。
    """
    try:
        from app.tasks.plan_tasks import rebuild_user_preference_embedding

        task = rebuild_user_preference_embedding.delay(user_id)
        return task.id
    except Exception:
        return None
