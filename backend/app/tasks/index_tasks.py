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
        from app.search.client import close_search_client, get_search_client

        # 重建 ES 客户端 —— 旧单例绑定到上一个事件循环，在新 loop 中必须重建
        await close_search_client()
        es_client = get_search_client()

        # 先创建索引 (如果不存在)
        await es_client.create_product_index()

        # 全量查询 — 预加载品牌和分类名称用于 ES 文档
        from snaptrip_shared.db.session import AsyncSessionLocal, async_engine

        try:
            await async_engine.dispose()
        except RuntimeError:
            pass  # 旧事件循环已关闭，连接无法清理，安全忽略

        from app.models.product.brand import PmsBrand
        from app.models.product.category import PmsCategory

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(PmsProduct).where(PmsProduct.is_deleted.is_(False)))
            products = result.scalars().all()

            # 预加载品牌名称映射
            brand_ids = {p.brand_id for p in products if p.brand_id}
            brand_map: dict = {}
            if brand_ids:
                brand_result = await session.execute(select(PmsBrand).where(PmsBrand.id.in_(brand_ids)))
                for b in brand_result.scalars().all():
                    brand_map[b.id] = b.name

            # 预加载分类名称映射
            category_ids = {p.category_id for p in products if p.category_id}
            category_map: dict = {}
            if category_ids:
                cat_result = await session.execute(select(PmsCategory).where(PmsCategory.id.in_(category_ids)))
                for c in cat_result.scalars().all():
                    category_map[c.id] = c.name

        # 批量索引
        docs = []
        for p in products:
            docs.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "sub_title": p.sub_title or "",
                    "keywords": p.keywords or "",
                    "category_id": str(p.category_id) if p.category_id else "",
                    "category_name": category_map.get(p.category_id, ""),
                    "brand_id": str(p.brand_id) if p.brand_id else "",
                    "brand_name": brand_map.get(p.brand_id, ""),
                    "price": float(p.price) if p.price else 0,
                    "promotion_price": float(p.promotion_price) if p.promotion_price else None,
                    "sale_count": p.sale_count or 0,
                    "stock": p.stock or 0,
                    "pics": p.pics or "",
                    "publish_status": p.publish_status,
                    "verify_status": p.verify_status,
                    "publish_time": p.created_at.isoformat() if p.created_at else None,
                }
            )

        success = await es_client.bulk_index_products(docs)
        logger.info("es_full_sync_done", total=len(products), success=success)
        return {"total": len(products), "indexed": success}

    return asyncio.run(_run())


@shared_task(name="sync_product_to_es_by_id")
def sync_product_to_es_by_id(product_id: str) -> bool:
    """同步单个商品到 ES —— 商品编辑后调用"""
    import asyncio

    async def _run():
        from uuid import UUID

        from snaptrip_shared.db.session import AsyncSessionLocal, async_engine

        try:
            await async_engine.dispose()
        except RuntimeError:
            pass  # 旧事件循环已关闭，连接无法清理，安全忽略

        from app.models.product.product import PmsProduct
        from app.search.client import close_search_client

        # 重建 ES 客户端 —— 旧单例绑定到上一个事件循环
        await close_search_client()

        from app.services.product_service import sync_product_to_es

        async with AsyncSessionLocal() as session:
            product = await session.get(PmsProduct, UUID(product_id))
            if not product:
                logger.warning("es_sync_product_not_found", product_id=product_id)
                return False
            await sync_product_to_es(session, product)
            return True

    return asyncio.run(_run())
