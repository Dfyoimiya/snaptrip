"""PlanRepository —— 数据库计划历史查询。

实现 PlanRepositoryPort，从 PostgreSQL plans 表聚合用户历史偏好。

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

import logging
from collections import Counter
from uuid import UUID

from snaptrip_shared.db.session import AsyncSessionLocal
from sqlalchemy import select

from marketplace.app.models.plan import Plan

logger = logging.getLogger(__name__)

_scene_type_map: dict[str, list[str]] = {
    "family": ["activity", "restaurant", "attraction"],
    "friends": ["restaurant", "cafe", "attraction"],
    "solo": ["cafe", "attraction", "activity"],
    "date": ["cafe", "attraction", "restaurant"],
}

_scene_mood_map: dict[str, list[str]] = {
    "family": ["亲子", "治愈", "拍照"],
    "friends": ["热闹", "聚餐", "拍照"],
    "solo": ["安静", "文艺", "治愈"],
    "date": ["浪漫", "安静", "拍照"],
}


class PlanRepository:
    """DB-backed 计划历史仓库。"""

    async def get_user_history(self, user_id: str) -> dict | None:
        """聚合用户历史计划的偏好统计。

        Returns:
            dict with keys: types, moods, dominant_scene.
            None when no history or DB error.
        """
        try:
            uid = UUID(user_id)
        except (ValueError, AttributeError):
            return None

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Plan)
                    .where(Plan.user_id == uid)
                    .order_by(Plan.created_at.desc())
                    .limit(20)
                )
                plans = result.scalars().all()
        except Exception:
            logger.warning("plan_repo_db_failed user_id=%s", user_id, exc_info=True)
            return None

        if not plans:
            return None

        scene_counter: Counter[str] = Counter()
        type_prefs: list[str] = []
        mood_prefs: list[str] = []

        for plan in plans:
            scene_counter[plan.group_type] += 1
            type_prefs.extend(_scene_type_map.get(plan.group_type, []))
            mood_prefs.extend(_scene_mood_map.get(plan.group_type, []))

        dominant_scene = scene_counter.most_common(1)[0][0] if scene_counter else None

        return {
            "types": list(set(type_prefs)),
            "moods": list(set(mood_prefs)),
            "dominant_scene": dominant_scene,
        }
