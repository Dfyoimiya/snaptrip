"""特征聚合服务 —— 从 Redis + PostgreSQL 聚合用户特征。

为 UserProfileAgent 提供数据基础:
  - Redis 滑动窗口: 实时行为统计 (views_1h, views_24h, clicks_1h)
  - PostgreSQL: 收藏偏好的类目 + 历史订单 RFM 计算
  - 返回 UserFeatureDict 供 LLM 分析生成画像

db_factory 接受 async session factory (每个请求创建独立会话),
memory 接受 MemoryService 实例。

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.models.member.member import UmsMemberFavorite
from app.models.order.order import OmsOrder, OmsOrderItem
from app.models.product.product import PmsProduct
from app.services.memory_service import MemoryService


class FeatureService:
    """用户特征聚合器 —— 从多数据源拼装用户特征画像。

    数据源优先级:
      1. Redis 缓存画像 (最快, 1h TTL)
      2. Redis 滑动窗口 (实时行为)
      3. PostgreSQL (收藏/订单持久化数据)
    """

    def __init__(self, db_factory, memory: MemoryService) -> None:
        self._db_factory = db_factory
        self._memory = memory

    async def get_user_features(self, user_id: uuid.UUID) -> dict[str, Any]:
        """聚合用户全部特征数据。

        Returns:
            {
                "user_id": str,
                "real_time": {views_1h, views_24h, clicks_1h, searches_1h, purchases_7d},
                "favorites": {count, category_ids, recent_product_ids},
                "purchase_history": {total_orders, rfm, recent_category_ids, avg_order_amount},
            }
        """
        uid = str(user_id)

        # 1. 检查缓存
        cached = await self._memory.get_cached_profile(uid)
        if cached:
            return cached

        # 2. 并行聚合各数据源
        real_time = await self._aggregate_realtime(uid)
        favorites = await self._aggregate_favorites(user_id)
        purchase_history = await self._aggregate_purchases(user_id)

        features = {
            "user_id": uid,
            "real_time": real_time,
            "favorites": favorites,
            "purchase_history": purchase_history,
        }

        # 3. 缓存 (1h TTL)
        await self._memory.cache_user_profile(uid, features, ttl=3600)

        return features

    async def _aggregate_realtime(self, uid: str) -> dict[str, int]:
        """从 Redis 滑动窗口聚合实时行为统计。"""
        views_1h = await self._memory.get_recent_behaviors(uid, "view", 3600)
        views_24h = await self._memory.get_recent_behaviors(uid, "view", 86400)
        clicks_1h = await self._memory.get_recent_behaviors(uid, "add_cart", 3600)
        searches_1h = await self._memory.get_recent_behaviors(uid, "search", 3600)
        purchases_7d = await self._memory.get_recent_behaviors(uid, "purchase", 86400 * 7)

        return {
            "views_1h": len(views_1h),
            "views_24h": len(views_24h),
            "clicks_1h": len(clicks_1h),
            "searches_1h": len(searches_1h),
            "purchases_7d": len(purchases_7d),
        }

    async def _aggregate_favorites(self, user_id: uuid.UUID) -> dict[str, Any]:
        """从 PostgreSQL 聚合收藏数据。"""
        async with self._db_factory() as db:
            fav_stmt = (
                select(UmsMemberFavorite.product_id)
                .where(UmsMemberFavorite.user_id == user_id)
                .order_by(UmsMemberFavorite.created_at.desc())
                .limit(50)
            )
            fav_result = await db.execute(fav_stmt)
            product_ids = [row[0] for row in fav_result.fetchall()]

            if not product_ids:
                return {"count": 0, "category_ids": [], "recent_product_ids": []}

            cat_stmt = (
                select(PmsProduct.category_id)
                .where(PmsProduct.id.in_(product_ids))
                .distinct()
            )
            cat_result = await db.execute(cat_stmt)
            category_ids = [str(row[0]) for row in cat_result.fetchall() if row[0]]

            return {
                "count": len(product_ids),
                "category_ids": category_ids,
                "recent_product_ids": [str(pid) for pid in product_ids[:10]],
            }

    async def _aggregate_purchases(self, user_id: uuid.UUID) -> dict[str, Any]:
        """从 PostgreSQL 聚合购买历史与 RFM 得分。"""
        async with self._db_factory() as db:
            order_stmt = (
                select(OmsOrder)
                .where(OmsOrder.member_id == user_id)
                .order_by(OmsOrder.created_at.desc())
                .limit(50)
            )
            result = await db.execute(order_stmt)
            orders = result.scalars().all()

            if not orders:
                return {
                    "total_orders": 0,
                    "rfm": {"recency": 0.0, "frequency": 0.0, "monetary": 0.0},
                    "recent_category_ids": [],
                    "avg_order_amount": 0.0,
                }

            now = datetime.now(UTC)
            days_since_last = max((now - orders[0].created_at).days, 0) if orders[0].created_at else 30
            total_amount = sum(float(o.total_amount or 0) for o in orders)
            avg_amount = total_amount / len(orders) if orders else 0.0

            rfm = {
                "recency": round(max(0, 1 - days_since_last / 30), 3),
                "frequency": round(min(1, len(orders) / 10), 3),
                "monetary": round(min(1, avg_amount / 1000), 3),
            }

            order_ids = [o.id for o in orders[:20]]
            if order_ids:
                cat_stmt = (
                    select(PmsProduct.category_id)
                    .select_from(OmsOrderItem)
                    .join(PmsProduct, OmsOrderItem.product_id == PmsProduct.id)
                    .where(OmsOrderItem.order_id.in_(order_ids))
                    .distinct()
                )
                cat_result = await db.execute(cat_stmt)
                category_ids = [str(row[0]) for row in cat_result.fetchall() if row[0]]
            else:
                category_ids = []

            return {
                "total_orders": len(orders),
                "rfm": rfm,
                "recent_category_ids": category_ids,
                "avg_order_amount": round(avg_amount, 2),
            }
