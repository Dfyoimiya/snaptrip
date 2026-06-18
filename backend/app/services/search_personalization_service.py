"""搜索个性化服务 —— 用户偏好 boost 计算。

对混合搜索结果应用个性化增强:
  - 类目偏好 boost: +0.15 ~ +0.20 (用户常浏览/购买的类目)
  - 价格匹配 boost: +0.10 (商品价格在用户偏好价格区间内)

用法:
    svc = SearchPersonalizationService(db_factory, memory)
    boosted = await svc.boost(products, user_id)

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text

logger = logging.getLogger(__name__)


class SearchPersonalizationService:
    """搜索个性化 boost 服务。"""

    def __init__(self, db_factory, memory) -> None:
        self._db_factory = db_factory
        self._memory = memory

    async def boost(self, products: list[dict], user_id: UUID | str) -> list[dict]:
        """对候选商品应用个性化 boost。

        boost = base_score + category_boost + price_boost
        """
        if not products or not user_id:
            return products

        uid = str(user_id)

        # 1. 获取用户偏好
        preferences = await self._get_user_preferences(uid)
        if not preferences:
            return products

        preferred_categories: set[str] = preferences.get("preferred_categories", set())
        price_range: tuple[float, float] = preferences.get("price_range", (0, float("inf")))

        if not preferred_categories:
            return products

        # 2. 应用 boost
        for p in products:
            cat_id = str(p.get("category_id", ""))
            price = float(p.get("price", 0) or 0)
            base = float(p.get("score", 0) or 0)

            boost = 0.0

            # 类目偏好 boost
            if cat_id and cat_id in preferred_categories:
                boost += 0.15  # 匹配用户偏好类目

            # 价格匹配 boost
            if price_range[0] <= price <= price_range[1]:
                boost += 0.10

            p["score"] = round(base + boost, 4)
            if boost > 0:
                p["_personalized"] = True

        # 按新分数重排
        return sorted(products, key=lambda x: x.get("score", 0), reverse=True)

    async def _get_user_preferences(self, uid: str) -> dict | None:
        """从 Redis 缓存 + DB 获取用户偏好。

        Returns:
            {
                "preferred_categories": {"cat-id-1", "cat-id-2", ...},
                "price_range": (min_price, max_price),
            }
        """
        cache_key = f"user_prefs:{uid}"

        # 检查 Redis 缓存 (1h TTL)
        cached = await self._memory.cache_get(cache_key)
        if cached:
            return cached

        prefs = await self._compute_user_preferences(uid)
        if prefs:
            await self._memory.cache_set(cache_key, prefs, ttl_s=3600)
        return prefs

    async def _compute_user_preferences(self, uid: str) -> dict | None:
        """从浏览和购买历史计算用户偏好。"""
        try:
            async with self._db_factory() as db:
                # 用户近期浏览的商品类目分布
                viewed_query = text("""
                    SELECT p.category_id, COUNT(*) AS cnt
                    FROM ums_member_behaviors b
                    JOIN pms_products p ON b.product_id = p.id
                    WHERE b.user_id = :uid
                      AND b.behavior_type = 'view'
                      AND b.created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY p.category_id
                    ORDER BY cnt DESC
                    LIMIT 5
                """)
                result = await db.execute(viewed_query, {"uid": uid})
                viewed_cats = {str(r[0]) for r in result.fetchall() if r[0]}

                # 用户购买的商品类目分布
                bought_query = text("""
                    SELECT p.category_id, COUNT(*) AS cnt
                    FROM ums_member_behaviors b
                    JOIN pms_products p ON b.product_id = p.id
                    WHERE b.user_id = :uid
                      AND b.behavior_type = 'purchase'
                      AND b.created_at >= NOW() - INTERVAL '90 days'
                    GROUP BY p.category_id
                    ORDER BY cnt DESC
                    LIMIT 5
                """)
                result = await db.execute(bought_query, {"uid": uid})
                bought_cats = {str(r[0]) for r in result.fetchall() if r[0]}

                # 用户价格偏好 (购买商品的价格中位数)
                price_query = text("""
                    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.price)
                    FROM ums_member_behaviors b
                    JOIN pms_products p ON b.product_id = p.id
                    WHERE b.user_id = :uid
                      AND b.behavior_type = 'purchase'
                      AND b.created_at >= NOW() - INTERVAL '90 days'
                """)
                result = await db.execute(price_query, {"uid": uid})
                median_price = result.scalar()

                preferred_categories = viewed_cats | bought_cats
                if not preferred_categories:
                    return None

                if median_price:
                    price_low = max(0, float(median_price) * 0.3)
                    price_high = float(median_price) * 2.5
                else:
                    price_low = 0
                    price_high = float("inf")

                return {
                    "preferred_categories": preferred_categories,
                    "price_range": (price_low, price_high),
                }
        except Exception as exc:
            logger.debug("search_personalization: compute preferences failed: %s", exc)
            return None
