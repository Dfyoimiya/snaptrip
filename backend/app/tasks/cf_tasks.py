"""协同过滤离线训练任务 —— Celery Beat 周期调度。

训练频率: 每 6 小时一次 (大促期间可临时改为 1 小时)。

用法:
    # 手动触发
    celery -A marketplace.app.celery_app call app.tasks.cf_tasks.train_cf_model

    # 定时调度 (在 celery_app.py 中配置 beat_schedule)
    # 每天 02:00, 08:00, 14:00, 20:00 执行

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import asyncio

from celery import shared_task
from snaptrip_shared.core.logging import get_logger

logger = get_logger(__name__)


@shared_task(
    name="train_cf_model",
    max_retries=2,
    default_retry_delay=300,  # 5 分钟后重试
    soft_time_limit=600,       # 10 分钟软超时 (防止训练阻塞)
    time_limit=900,            # 15 分钟硬超时
)
def train_cf_model() -> dict:
    """训练 ALS 协同过滤模型。

    流程:
      1. 从 ums_member_behaviors 构建 user-item 矩阵
      2. 训练 ALS (factors=64)
      3. 持久化 item vectors → pms_product_cf_vectors
      4. 持久化 user vectors → Redis

    Returns:
        {"model_version": str, "n_users": int, "n_items": int, ...}
    """
    async def _run():
        from snaptrip_shared.db.session import AsyncSessionLocal

        from app.services.memory_service import MemoryService
        from app.services.collaborative_filtering_service import CollaborativeFilteringService

        memory = MemoryService()
        await memory.start()

        try:
            svc = CollaborativeFilteringService(
                db_factory=AsyncSessionLocal,
                memory=memory,
            )
            result = await svc.train()
            logger.info("cf_train_complete", extra=result)
            return result
        finally:
            await memory.stop()

    return asyncio.run(_run())
