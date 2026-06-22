"""商品 Embedding 生成任务 —— Celery Beat 周期调度。

调度频率: 每小时一次 (增量更新新品/无 embedding 商品)。

用法:
    # 手动触发全量
    celery -A marketplace.app.celery_app call app.tasks.embedding_tasks.generate_all_embeddings

    # 手动触增量
    celery -A marketplace.app.celery_app call app.tasks.embedding_tasks.generate_incremental_embeddings

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import asyncio

from celery import shared_task
from snaptrip_shared.core.logging import get_logger

logger = get_logger(__name__)


@shared_task(
    name="generate_incremental_embeddings",
    max_retries=2,
    default_retry_delay=120,  # 2 分钟后重试
    soft_time_limit=300,  # 5 分钟软超时
    time_limit=600,  # 10 分钟硬超时
)
def generate_incremental_embeddings() -> dict:
    """增量生成: 为新品/无 embedding 商品生成 384 维语义向量。

    流程:
      1. LEFT JOIN 查询已上架但 pms_product_embeddings 中无记录的商品
      2. 拼接商品文本 (name + sub_title + keywords)
      3. 调用 all-MiniLM-L6-v2 生成向量
      4. UPSERT 写入 pms_product_embeddings

    Returns:
        {"embedded": int, "skipped": int, "total": int}
    """

    async def _run():
        from snaptrip_shared.db.session import AsyncSessionLocal, async_engine

        try:
            await async_engine.dispose()
        except RuntimeError:
            pass

        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService(db_factory=AsyncSessionLocal)
        result = await svc.generate_incremental()
        logger.info("embedding_incremental_complete", extra=result)
        return result

    return asyncio.run(_run())


@shared_task(
    name="generate_all_embeddings",
    max_retries=1,
    default_retry_delay=300,
    soft_time_limit=1800,  # 30 分钟软超时 (全量可能很大)
    time_limit=3600,  # 1 小时硬超时
)
def generate_all_embeddings() -> dict:
    """全量生成: 为所有已上架商品生成 embedding。

    仅在模型升级或首次初始化时手动触发。
    """

    async def _run():
        from snaptrip_shared.db.session import AsyncSessionLocal, async_engine

        try:
            await async_engine.dispose()
        except RuntimeError:
            pass

        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService(db_factory=AsyncSessionLocal)
        result = await svc.generate_all()
        logger.info("embedding_all_complete", extra=result)
        return result

    return asyncio.run(_run())
