"""
【Celery 异步任务 - ES 索引用步】

知识点速查:
  - Celery @shared_task: 声明异步任务，可被 Celery Worker 自动发现和执行
    "shared" 表示不绑定特定 Celery 实例，任何注册了 tasks 的 worker 都能执行
  - 为什么批量索引用 Celery 而不是直接在 API 中做？
    同步创建 10000 个商品的索引可能耗时 30 秒+
    API 请求应该在 200ms 内返回 → 异步任务处理耗时操作
  - .delay(): 发送任务到消息队列(Redis)，不阻塞当前请求

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from celery import shared_task
from snaptrip_shared.core.logging import get_logger

logger = get_logger(__name__)


@shared_task(name="sync_all_products_to_es", max_retries=3, default_retry_delay=60)
def sync_all_products_to_es() -> dict:
    """
    全量同步商品到 Elasticsearch。

    使用场景:
      - ES 索引重建后，重新同步所有商品
      - 定时任务 (每天凌晨 3 点) 全量刷新保证最终一致性
      - 执行: celery -A marketplace.app.celery_app call app.tasks.index_tasks.sync_all_products_to_es
    """
    import asyncio

    async def _run():
        from sqlalchemy import select

        from app.models.product.product import PmsProduct
        from app.search.client import get_search_client

        # 先创建索引 (如果不存在)
        await get_search_client().create_product_index()

        # 全量查询
        from snaptrip_shared.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PmsProduct).where(PmsProduct.is_deleted.is_(False))
            )
            products = result.scalars().all()

        # 批量索引
        docs = []
        for p in products:
            docs.append({
                "id": str(p.id),
                "name": p.name,
                "sub_title": p.sub_title or "",
                "keywords": p.keywords or "",
                "category_id": str(p.category_id) if p.category_id else "",
                "brand_id": str(p.brand_id) if p.brand_id else "",
                "price": float(p.price) if p.price else 0,
                "promotion_price": float(p.promotion_price) if p.promotion_price else None,
                "sale_count": p.sale_count or 0,
                "stock": p.stock or 0,
                "pics": p.pics or "",
                "publish_status": p.publish_status,
                "verify_status": p.verify_status,
            })

        success = await get_search_client().bulk_index_products(docs)
        logger.info("es_full_sync_done", total=len(products), success=success)
        return {"total": len(products), "indexed": success}

    return asyncio.get_event_loop().run_until_complete(_run())


@shared_task(name="sync_product_to_es_by_id")
def sync_product_to_es_by_id(product_id: str) -> bool:
    """同步单个商品到 ES —— 商品编辑后调用"""
    import asyncio

    async def _run():
        from uuid import UUID

        from snaptrip_shared.db.session import AsyncSessionLocal

        from app.models.product.product import PmsProduct
        from app.services.product_service import _sync_product_to_es

        async with AsyncSessionLocal() as session:
            product = await session.get(PmsProduct, UUID(product_id))
            if not product:
                logger.warning("es_sync_product_not_found", product_id=product_id)
                return False
            await _sync_product_to_es(product)
            return True

    return asyncio.get_event_loop().run_until_complete(_run())
