"""UnifiedRecallService — 多路召回统一编排。

5 路召回并行执行, 独立降级, 输出归一化候选池:
  Channel 1: ES BM25 关键词召回 (ik_smart 中文分词)
  Channel 2: pgvector 语义向量召回 (384-dim all-MiniLM-L6-v2)
  Channel 3: Collaborative Filtering 召回 (64-dim ALS, 仅登录用户)
  Channel 4: 热门/趋势商品召回 (Redis ZSET 24h 滑动窗口)
  Channel 5: DB 属性/标签精确匹配 (LIKE + 分类/品牌筛选)

每条通道独立可降级, 输出格式: {"product_id", "score", "_source", ...}

使用场景:
  - HybridSearchService 混合搜索 (搜索页)
  - ProductRecAgent 导购 Agent 管道 (不再调 HTTP API)
  - HomeFeed 首页推荐 (替代旧 RecommendationSupervisor)

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.models.product.product import PmsProduct

logger = logging.getLogger(__name__)

# 默认各通道召回数量
DEFAULT_CHANNEL_BUDGETS: dict[str, int] = {
    "es": 60,
    "vector": 40,
    "cf": 30,
    "trending": 20,
    "attribute": 20,
}

# 通道对应的 _source 标签
CHANNEL_SOURCE_MAP: dict[str, str] = {
    "es": "es",
    "vector": "vector",
    "cf": "cf",
    "trending": "trending",
    "attribute": "attribute",
}


class UnifiedRecallService:
    """多路召回统一编排服务。

    所有通道并行执行, 单通道失败不影响其他通道。
    供后端搜索、首页推荐、Agent 管道共用。

    用法:
        recall = UnifiedRecallService(
            es_client=es_client,
            vector_service=vector_svc,
            cf_service=cf_svc,
            trending_service=trending_svc,
            db_factory=AsyncSessionLocal,
        )
        candidates = await recall.recall(
            query="笔记本电脑",
            user_id="uuid-xxx",
            embedding=[0.1, 0.2, ...],
            filters={"category_id": "...", "brand_id": "...", "min_price": 1000},
            channels=["es", "vector", "cf", "trending"],
            budget=100,
        )
    """

    def __init__(
        self,
        es_client: Any = None,
        vector_service: Any = None,
        cf_service: Any = None,
        trending_service: Any = None,
        db_factory: Any = None,
    ) -> None:
        self._es = es_client
        self._vector = vector_service
        self._cf = cf_service
        self._trending = trending_service
        self._db_factory = db_factory

    async def recall(
        self,
        query: str | None = None,
        user_id: UUID | str | None = None,
        embedding: list[float] | None = None,
        filters: dict[str, Any] | None = None,
        channels: list[str] | None = None,
        budget: int = 100,
    ) -> list[dict]:
        """多路召回入口。

        Args:
            query: 搜索关键词 (用于 ES + attribute 通道)
            user_id: 用户 ID (用于 CF 通道)
            embedding: 查询向量 (用于 vector 通道, 若不提供则不启用)
            filters: 过滤条件 {category_id, brand_id, min_price, max_price}
            channels: 启用的通道列表, None=全部启用
            budget: 最终候选池大小上限

        Returns:
            候选商品列表 [{product_id, score, _source, name, price, ...}]
        """
        flt = filters or {}
        ch_list = channels or list(DEFAULT_CHANNEL_BUDGETS.keys())

        # 构建并行任务
        tasks: dict[str, asyncio.Task] = {}
        for ch_name in ch_list:
            limit = DEFAULT_CHANNEL_BUDGETS.get(ch_name, 20)
            coro = self._recall_channel(
                ch_name, query, user_id, embedding, flt, limit
            )
            tasks[ch_name] = asyncio.ensure_future(coro)

        # 等待所有通道完成 (每个独立降级)
        results: dict[str, list[dict]] = {}
        for ch_name, task in tasks.items():
            try:
                results[ch_name] = await task
            except Exception as exc:
                logger.warning("recall_service: channel %s failed: %s", ch_name, exc)
                results[ch_name] = []

        # 去重合并 (同 product_id 保留最高分)
        merged: dict[str, dict] = {}
        for ch_name, items in results.items():
            source_tag = CHANNEL_SOURCE_MAP.get(ch_name, ch_name)
            for item in items:
                pid = str(item.get("product_id", ""))
                if not pid:
                    continue
                score = float(item.get("score", 0) or 0)
                if pid in merged:
                    merged[pid]["_sources"].append(source_tag)
                    if score > merged[pid]["score"]:
                        merged[pid]["score"] = score
                else:
                    merged[pid] = {
                        "product_id": pid,
                        "name": item.get("name", ""),
                        "price": _to_float(item.get("price", 0)),
                        "sale_count": item.get("sale_count", 0) or 0,
                        "image_url": item.get("image_url", item.get("default_pic", "")),
                        "brand_name": item.get("brand_name", ""),
                        "category_id": str(item.get("category_id", "")),
                        "stock": item.get("stock", 0) or 0,
                        "score": score,
                        "_sources": [source_tag],
                    }

        candidates = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
        logger.info(
            "recall_service: query=%s channels=%s merged=%d budget=%d",
            query,
            ch_list,
            len(candidates),
            budget,
        )
        return candidates[:budget]

    # ── Per-channel dispatch ───────────────────────────────────────────────

    async def _recall_channel(
        self,
        ch_name: str,
        query: str | None,
        user_id: UUID | str | None,
        embedding: list[float] | None,
        filters: dict,
        limit: int,
    ) -> list[dict]:
        """Dispatch to the right channel implementation."""
        if ch_name == "es":
            return await self._es_recall(query, filters, limit)
        elif ch_name == "vector":
            return await self._vector_recall(query, embedding, filters, limit)
        elif ch_name == "cf":
            return await self._cf_recall(user_id, limit)
        elif ch_name == "trending":
            return await self._trending_recall(limit)
        elif ch_name == "attribute":
            return await self._attribute_recall(query, filters, limit)
        else:
            logger.debug("recall_service: unknown channel %s", ch_name)
            return []

    # ── Channel 1: ES BM25 ─────────────────────────────────────────────────

    async def _es_recall(
        self,
        query: str | None,
        filters: dict,
        limit: int,
    ) -> list[dict]:
        if not self._es or not query:
            return []
        try:
            raw = await self._es.search_products(
                keyword=query,
                category_id=filters.get("category_id"),
                brand_id=filters.get("brand_id"),
                min_price=filters.get("min_price"),
                max_price=filters.get("max_price"),
                sort_by="default",
                page=1,
                page_size=min(limit, 60),
            )
            items = raw.get("items", []) if isinstance(raw, dict) else []
            for item in items:
                item["_source"] = "es"
                if item.get("score") is None:
                    item["score"] = 0.0
            return items
        except Exception as exc:
            logger.warning("recall_service: ES recall failed: %s", exc)
            return []

    # ── Channel 2: pgvector Semantic ───────────────────────────────────────

    async def _vector_recall(
        self,
        query: str | None,
        embedding: list[float] | None,
        filters: dict,
        limit: int,
    ) -> list[dict]:
        if not self._vector:
            return []
        try:
            # 如果外部没有提供 embedding, 尝试从 query 生成
            if embedding is None and query:
                embedding = await self._get_query_embedding(query)
            if embedding is None:
                return []

            results = await self._vector.search_by_text_embedding(
                embedding,
                limit=limit,
                category_id=filters.get("category_id"),
            )
            for r in results:
                r["_source"] = "vector"
            return results
        except Exception as exc:
            logger.warning("recall_service: vector recall failed: %s", exc)
            return []

    # ── Channel 3: Collaborative Filtering ─────────────────────────────────

    async def _cf_recall(
        self,
        user_id: UUID | str | None,
        limit: int,
    ) -> list[dict]:
        if not self._cf or not user_id:
            return []
        try:
            results = await self._cf.recommend(user_id, n=limit)
            for r in results:
                r["_source"] = "cf"
            return results
        except Exception as exc:
            logger.warning("recall_service: CF recall failed: %s", exc)
            return []

    # ── Channel 4: Trending/Popularity ─────────────────────────────────────

    async def _trending_recall(self, limit: int) -> list[dict]:
        if not self._trending:
            return []
        try:
            results = await self._trending.get_trending_products(
                window_hours=24,
                limit=limit,
            )
            # trending results have "trending_score"; normalize to "score"
            for r in results:
                r["score"] = r.get("trending_score", 0)
                r["_source"] = "trending"
            return results
        except Exception as exc:
            logger.warning("recall_service: trending recall failed: %s", exc)
            return []

    # ── Channel 5: Attribute/Label Match (DB) ──────────────────────────────

    async def _attribute_recall(
        self,
        query: str | None,
        filters: dict,
        limit: int,
    ) -> list[dict]:
        """DB 属性/标签精确匹配: keyword ILIKE + category/brand/price 过滤。

        适用场景: 精确筛选 (如 "华为手机 5000以下")。
        """
        if not self._db_factory:
            return []
        try:
            async with self._db_factory() as db:
                base = (
                    select(PmsProduct)
                    .where(PmsProduct.publish_status == 1)
                    .where(PmsProduct.verify_status == 1)
                    .where(PmsProduct.is_deleted.is_(False))
                )

                if query:
                    base = base.where(PmsProduct.name.ilike(f"%{query}%"))
                if filters.get("category_id"):
                    base = base.where(
                        PmsProduct.category_id == filters["category_id"]
                    )
                if filters.get("brand_id"):
                    base = base.where(PmsProduct.brand_id == filters["brand_id"])
                if filters.get("min_price") is not None:
                    base = base.where(PmsProduct.price >= filters["min_price"])
                if filters.get("max_price") is not None:
                    base = base.where(PmsProduct.price <= filters["max_price"])

                result = await db.execute(
                    base.order_by(PmsProduct.sale_count.desc()).limit(limit)
                )
                products = result.scalars().all()

                return [
                    {
                        "product_id": str(p.id),
                        "name": p.name or "",
                        "price": float(p.price) if p.price else 0,
                        "sale_count": p.sale_count or 0,
                        "image_url": p.default_pic or "",
                        "brand_name": getattr(p, "brand_name", "") or "",
                        "category_id": str(p.category_id) if p.category_id else "",
                        "stock": getattr(p, "stock", 100) or 100,
                        "score": _attr_score(p, query),
                        "_source": "attribute",
                    }
                    for p in products
                ]
        except Exception as exc:
            logger.warning("recall_service: attribute recall failed: %s", exc)
            return []

    # ── Embedding Helper ───────────────────────────────────────────────────

    async def _get_query_embedding(self, query: str) -> list[float] | None:
        """获取查询文本的 384 维 embedding (复用 HybridSearchService 的模型)。"""
        try:
            from app.services.hybrid_search_service import _get_local_embedding_model

            model = _get_local_embedding_model()
            embedding = await asyncio.to_thread(
                model.encode, query, normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as exc:
            logger.debug("recall_service: query embedding failed: %s", exc)
            return None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _to_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _attr_score(product: PmsProduct, query: str | None) -> float:
    """属性匹配评分: 精确匹配 > 标签匹配 > 名称匹配。"""
    score = 0.3  # base score for attribute channel
    if not query:
        return score
    q = query.lower()
    name_lower = (product.name or "").lower()
    # Exact name match boost
    if q == name_lower:
        score += 0.4
    elif q in name_lower:
        score += 0.2
    # Keywords match boost
    keywords = (getattr(product, "keywords", "") or "").lower()
    if q in keywords:
        score += 0.15
    # Brand match boost
    brand = (getattr(product, "brand_name", "") or "").lower()
    if q in brand:
        score += 0.1
    return min(score, 1.0)
