"""首页多维度推荐 Feed API —— GET /api/v1/portal/home/feed

聚合 5 个推荐数据源, 每个 section 独立降级:
  Row 1: 猜你喜欢 (个性化, Agent pipeline + vector recall)
  Row 2: 热门推荐 (Redis trending 滑动窗口)
  Row 3: 新品上市 (DB created_at DESC)
  Row 4: 浏览历史 (Redis behavior ZSET)
  Row 5: 搜索发现 (Redis query velocity)

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import AsyncSessionLocal
from sqlalchemy import select

from app.models.product.product import PmsProduct
from app.schemas.homefeed import (
    FeedProduct,
    FeedSection,
    FeedSectionType,
    HomeFeedResponse,
    SearchDiscoveryItem,
)
from app.services.autocomplete_service import AutocompleteService
from app.services.memory_service import MemoryService
from app.services.trending_service import TrendingService
from app.services.vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal/home", tags=["Portal - 首页"])


def _get_memory(request: Request) -> MemoryService:
    return request.app.state.memory


def _get_trending(request: Request) -> TrendingService:
    svc = request.app.state.trending_service
    if svc is None:
        raise RuntimeError("TrendingService not initialized")
    return svc


def _get_vector(request: Request) -> VectorSearchService:
    svc = request.app.state.vector_search_service
    if svc is None:
        raise RuntimeError("VectorSearchService not initialized")
    return svc


def _get_autocomplete(request: Request) -> AutocompleteService:
    svc = request.app.state.autocomplete_service
    if svc is None:
        raise RuntimeError("AutocompleteService not initialized")
    return svc


def _resolve_user_id(request: Request) -> UUID | None:
    """从 Authorization header 解析 user_id (可选认证)。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        from marketplace.app.core.security import decode_access_token

        token = auth.removeprefix("Bearer ").strip()
        payload = decode_access_token(token)
        sub = payload.get("sub", "")
        return UUID(sub) if sub else None
    except Exception:
        return None


@router.get("/feed", summary="首页多维度推荐聚合")
async def home_feed(
    request: Request,
    memory: MemoryService = Depends(_get_memory),
    trending: TrendingService = Depends(_get_trending),
    vector: VectorSearchService = Depends(_get_vector),
    user_id: UUID | None = Depends(_resolve_user_id),
    limit: int = Query(10, ge=1, le=30),
):
    """并发聚合 5 个推荐数据源。

    每个 section 使用独立的 DB session，允许并发执行。
    """
    session_id = request.headers.get("X-Session-Id", "")
    tasks = []

    # Row 1: 猜你喜欢 (最复杂, 涉及多路召回)
    tasks.append(_build_guess_you_like(request, memory, vector, user_id, session_id, limit))

    # Row 2: 热门推荐 (Redis trending)
    tasks.append(_build_trending_now(trending, limit))

    # Row 3: 新品上市
    tasks.append(_build_new_arrivals(user_id, limit))

    # Row 4: 浏览历史
    tasks.append(_build_recently_viewed(memory, user_id, session_id, limit))

    # Row 5: 搜索发现
    tasks.append(_build_search_discovery(trending, limit=8))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    sections: list[FeedSection] = []
    for result in results:
        if isinstance(result, FeedSection):
            sections.append(result)
        elif isinstance(result, Exception):
            logger.warning("HomeFeed: section failed: %s", result)
        # None = skipped (e.g. no browsing history)

    return success(
        HomeFeedResponse(
            sections=sections,
            user_id=str(user_id) if user_id else None,
            session_id=session_id or None,
        ).model_dump()
    )


async def _build_guess_you_like(
    request: Request,
    memory: MemoryService,
    vector: VectorSearchService,
    user_id: UUID | None,
    session_id: str,
    limit: int,
) -> FeedSection:
    """Row 1: 猜你喜欢 — 多路召回融合。

    有 user_id: vector(40%) + recent_views(30%) + hot(30%) → agent rerank
    无 user_id: 纯热门兜底
    """
    try:
        candidates: list[dict] = []
        total_budget = limit * 3

        if user_id:
            # Vector recall
            try:
                vec_results = await vector.search_similar_by_favorites(user_id, limit=int(total_budget * 0.4))
                candidates.extend(vec_results)
            except Exception as exc:
                logger.debug("guess_you_like: vector recall failed: %s", exc)

            # Recent views from Redis
            try:
                viewed_ids = await memory.get_recent_viewed_products(str(user_id), limit=int(total_budget * 0.3))
                if viewed_ids:
                    async with AsyncSessionLocal() as session:
                        from sqlalchemy import select as sa_select

                        stmt = (
                            sa_select(PmsProduct)
                            .where(
                                PmsProduct.id.in_([UUID(pid) for pid in viewed_ids if _is_valid_uuid(pid)]),
                                PmsProduct.publish_status == 1,
                                PmsProduct.verify_status == 1,
                                PmsProduct.is_deleted.is_(False),
                            )
                            .limit(int(total_budget * 0.3))
                        )
                        result = await session.execute(stmt)
                        for p in result.scalars().all():
                            candidates.append(_product_to_dict(p, source="recent_view"))
            except Exception as exc:
                logger.debug("guess_you_like: recent views failed: %s", exc)

        # Hot recall (fill remaining)
        try:
            hot_limit = total_budget - len(candidates)
            if hot_limit > 0:
                async with AsyncSessionLocal() as session:
                    stmt = (
                        select(PmsProduct)
                        .where(
                            PmsProduct.publish_status == 1,
                            PmsProduct.verify_status == 1,
                            PmsProduct.is_deleted.is_(False),
                        )
                        .order_by(PmsProduct.sale_count.desc())
                        .limit(hot_limit)
                    )
                    result = await session.execute(stmt)
                    for p in result.scalars().all():
                        candidates.append(_product_to_dict(p, source="hot"))
        except Exception as exc:
            logger.debug("guess_you_like: hot recall failed: %s", exc)

        # Dedup
        seen: set[str] = set()
        deduped: list[dict] = []
        for c in candidates:
            pid = c.get("product_id", "")
            if pid and pid not in seen:
                seen.add(pid)
                deduped.append(c)

        # Agent pipeline rerank (if available)
        products = deduped[:total_budget]
        marketing_copies: dict[str, str] = {}
        try:
            supervisor = request.app.state.recommendation_supervisor
            from agent.schemas.recommendation import RecommendationRequest, RecommendationScene

            req = RecommendationRequest(
                user_id=str(user_id) if user_id else None,
                session_id=session_id or None,
                scene=RecommendationScene.HOMEPAGE,
                num_items=limit,
            )
            # 预置 candidates 到 supervisor
            resp = await supervisor.recommend(req)
            if resp.products:
                products = [
                    {
                        "product_id": p.product_id,
                        "name": p.name,
                        "price": p.price,
                        "image_url": p.image_url,
                        "brand_name": p.brand_name,
                        "category_id": p.category_id,
                        "sale_count": p.sale_count,
                        "stock": p.stock,
                        "score": p.score,
                        "_source": "agent_rerank",
                    }
                    for p in resp.products
                ]
                for copy_item in resp.copies:
                    marketing_copies[copy_item.get("product_id", "")] = copy_item.get("copy", "")
        except Exception as exc:
            logger.debug("guess_you_like: agent rerank failed: %s", exc)

        feed_products = [
            FeedProduct(
                product_id=p.get("product_id", ""),
                name=p.get("name", ""),
                price=p.get("price", 0),
                image_url=p.get("image_url", ""),
                brand_name=p.get("brand_name", ""),
                category_id=p.get("category_id", ""),
                sale_count=p.get("sale_count", 0),
                stock=p.get("stock", 0),
                score=p.get("score", 0),
                marketing_copy=marketing_copies.get(p.get("product_id", ""), ""),
                promotion_price=p.get("promotion_price"),
                promotion_type=p.get("promotion_type", 0),
                new_status=p.get("new_status", 0),
                recommend_status=p.get("recommend_status", 0),
            )
            for p in products[:limit]
        ]

        return FeedSection(
            section_type=FeedSectionType.GUESS_YOU_LIKE,
            title="AI 猜你喜欢" if user_id else "热门推荐",
            sub_title="基于你的浏览和收藏" if user_id else "精选好物",
            products=feed_products,
        )
    except Exception as exc:
        logger.error("guess_you_like section failed: %s", exc)
        # 降级: 纯热门
        return await _build_trending_fallback(limit)


async def _build_trending_now(
    trending: TrendingService,
    limit: int,
) -> FeedSection:
    """Row 2: 热门推荐 — Redis trending 滑动窗口。"""
    try:
        trending_products = await trending.get_trending_products(window_hours=24, limit=limit * 2)
        product_ids = [p["product_id"] for p in trending_products if _is_valid_uuid(p["product_id"])]
        if not product_ids:
            return await _build_trending_fallback(limit)

        # 从 DB 解析完整商品数据
        async with AsyncSessionLocal() as session:
            id_map = await _resolve_products_by_ids(session, product_ids)
        feed_products = []
        for tp in trending_products:
            pid = tp["product_id"]
            if pid in id_map:
                p = id_map[pid]
                feed_products.append(
                    FeedProduct(
                        product_id=pid,
                        name=p.get("name", ""),
                        price=p.get("price", 0),
                        image_url=p.get("image_url", ""),
                        brand_name=p.get("brand_name", ""),
                        category_id=p.get("category_id", ""),
                        sale_count=p.get("sale_count", 0),
                        stock=p.get("stock", 0),
                        score=tp.get("trending_score", 0),
                    )
                )

        return FeedSection(
            section_type=FeedSectionType.TRENDING_NOW,
            title="热门推荐",
            sub_title="24小时热销排行",
            products=feed_products[:limit],
        )
    except Exception as exc:
        logger.warning("trending_now section failed: %s", exc)
        return await _build_trending_fallback(limit)


async def _build_new_arrivals(
    user_id: UUID | None,
    limit: int,
) -> FeedSection:
    """Row 3: 新品上市。"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(PmsProduct)
                .where(
                    PmsProduct.publish_status == 1,
                    PmsProduct.verify_status == 1,
                    PmsProduct.is_deleted.is_(False),
                )
                .order_by(PmsProduct.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            products = result.scalars().all()

        return FeedSection(
            section_type=FeedSectionType.NEW_ARRIVALS,
            title="新品上市",
            sub_title="最新上架，抢先体验",
            products=[
                FeedProduct(
                    product_id=str(p.id),
                    name=p.name or "",
                    price=float(p.price) if p.price else 0,
                    image_url=p.default_pic or "",
                    brand_name=getattr(p, "brand_name", "") or "",
                    category_id=str(p.category_id) if p.category_id else "",
                    sale_count=p.sale_count or 0,
                    stock=getattr(p, "stock", 100) or 100,
                    new_status=getattr(p, "new_status", 0),
                    recommend_status=getattr(p, "recommend_status", 0),
                )
                for p in products
            ],
        )
    except Exception as exc:
        logger.warning("new_arrivals section failed: %s", exc)
        return FeedSection(
            section_type=FeedSectionType.NEW_ARRIVALS,
            title="新品上市",
            sub_title="最新上架",
            products=[],
        )


async def _build_recently_viewed(
    memory: MemoryService,
    user_id: UUID | None,
    session_id: str,
    limit: int,
) -> FeedSection | None:
    """Row 4: 浏览历史。

    仅登录用户有数据, 匿名/无数据时返回 None (前端隐藏)。
    """
    if not user_id and not session_id:
        return None
    try:
        uid = str(user_id) if user_id else session_id
        product_ids = await memory.get_recent_viewed_products(uid, limit=limit)
        if not product_ids:
            return None

        async with AsyncSessionLocal() as session:
            id_map = await _resolve_products_by_ids(session, product_ids)
        feed_products = []
        for pid in product_ids:
            if pid in id_map:
                p = id_map[pid]
                feed_products.append(
                    FeedProduct(
                        product_id=pid,
                        name=p.get("name", ""),
                        price=p.get("price", 0),
                        image_url=p.get("image_url", ""),
                        brand_name=p.get("brand_name", ""),
                        category_id=p.get("category_id", ""),
                        sale_count=p.get("sale_count", 0),
                        stock=p.get("stock", 0),
                    )
                )

        if not feed_products:
            return None

        return FeedSection(
            section_type=FeedSectionType.RECENTLY_VIEWED,
            title="浏览历史",
            sub_title="继续探索你感兴趣的",
            products=feed_products,
        )
    except Exception as exc:
        logger.warning("recently_viewed section failed: %s", exc)
        return None


# 搜索发现兜底热词 (Redis 无数据时使用)
_SEARCH_DISCOVERY_FALLBACK = [
    ("手机", 100),
    ("笔记本电脑", 85),
    ("耳机", 70),
    ("运动鞋", 65),
    ("手表", 55),
    ("连衣裙", 50),
    ("双肩包", 45),
    ("蓝牙音箱", 40),
]


async def _build_search_discovery(
    trending: TrendingService,
    limit: int = 8,
) -> FeedSection:
    """Row 5: 搜索发现 — 热门搜索 query。"""
    try:
        hot_queries = await trending.get_hot_queries_simple(window_minutes=30, limit=limit)
        if not hot_queries:
            # 兜底: 使用预设热词
            hot_queries = [{"query": q, "count": c} for q, c in _SEARCH_DISCOVERY_FALLBACK[:limit]]
        suggestions = [SearchDiscoveryItem(query=q["query"], count=q["count"]) for q in hot_queries]
        return FeedSection(
            section_type=FeedSectionType.SEARCH_DISCOVERY,
            title="搜索发现",
            sub_title="大家都在搜",
            suggestions=suggestions,
        )
    except Exception as exc:
        logger.warning("search_discovery section failed: %s", exc)
        suggestions = [SearchDiscoveryItem(query=q, count=c) for q, c in _SEARCH_DISCOVERY_FALLBACK[:limit]]
        return FeedSection(
            section_type=FeedSectionType.SEARCH_DISCOVERY,
            title="搜索发现",
            sub_title="大家都在搜",
            suggestions=suggestions,
        )


# ─── Helpers ───


async def _build_trending_fallback(limit: int) -> FeedSection:
    """热门推荐降级: 直接查 DB sale_count DESC。"""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(PmsProduct)
            .where(
                PmsProduct.publish_status == 1,
                PmsProduct.verify_status == 1,
                PmsProduct.is_deleted.is_(False),
            )
            .order_by(PmsProduct.sale_count.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        products = result.scalars().all()
    return FeedSection(
        section_type=FeedSectionType.TRENDING_NOW,
        title="热门推荐",
        sub_title="精选好物，品质保障",
        products=[_product_to_feed(p, source="db_fallback") for p in products],
    )


async def _resolve_products_by_ids(
    db: AsyncSession,
    product_ids: list[str],
) -> dict[str, dict]:
    """批量解析商品 ID 到完整数据。"""
    if not product_ids:
        return {}
    valid_ids = [UUID(pid) for pid in product_ids if _is_valid_uuid(pid)]
    if not valid_ids:
        return {}
    stmt = select(PmsProduct).where(PmsProduct.id.in_(valid_ids))
    result = await db.execute(stmt)
    return {str(p.id): _product_to_dict(p, source="resolved") for p in result.scalars().all()}


def _product_to_dict(p, source: str = "") -> dict:
    return {
        "product_id": str(p.id),
        "name": p.name or "",
        "price": float(p.price) if p.price else 0,
        "image_url": p.default_pic or "",
        "brand_name": getattr(p, "brand_name", "") or "",
        "category_id": str(p.category_id) if p.category_id else "",
        "sale_count": p.sale_count or 0,
        "stock": getattr(p, "stock", 100) or 100,
        "score": 0.5,
        "_source": source,
        "promotion_price": float(p.promotion_price) if getattr(p, "promotion_price", None) else None,
        "promotion_type": getattr(p, "promotion_type", 0) or 0,
        "new_status": getattr(p, "new_status", 0) or 0,
        "recommend_status": getattr(p, "recommend_status", 0) or 0,
    }


def _product_to_feed(p, source: str = "") -> FeedProduct:
    d = _product_to_dict(p, source)
    return FeedProduct(
        product_id=d["product_id"],
        name=d["name"],
        price=d["price"],
        image_url=d["image_url"],
        brand_name=d["brand_name"],
        category_id=d["category_id"],
        sale_count=d["sale_count"],
        stock=d["stock"],
        score=d["score"],
        promotion_price=d.get("promotion_price"),
        promotion_type=d.get("promotion_type", 0),
        new_status=d.get("new_status", 0),
        recommend_status=d.get("recommend_status", 0),
    )


def _is_valid_uuid(s: str) -> bool:
    try:
        UUID(s)
        return True
    except (ValueError, AttributeError):
        return False
