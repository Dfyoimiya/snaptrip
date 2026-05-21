"""UserProfileRepository —— 数据库用户画像查询。

实现 UserProfileRepositoryPort，从 PostgreSQL user_profiles 表查询画像数据。

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

_DEFAULT_FAMILY: dict = {"child_age": None, "diet": "无偏好", "allergens": []}


class UserProfileRepository:
    """DB-backed 用户画像仓库。"""

    async def get_profile(self, user_id: str) -> dict | None:
        """从 user_profiles 表查询画像。

        Returns:
            dict with keys: preference_embedding, preferences, travel_style.
            None when user not found or DB error.
        """
        from uuid import UUID

        try:
            uid = UUID(user_id)
        except (ValueError, AttributeError):
            return None

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(UserProfile).where(UserProfile.user_id == uid))
                profile = result.scalar_one_or_none()
        except Exception:
            logger.warning("user_profile_repo_db_failed user_id=%s", user_id, exc_info=True)
            return None

        if profile is None:
            return None

        prefs = profile.preferences or _DEFAULT_FAMILY
        return {
            "preference_embedding": profile.preference_embedding,
            "preferences": prefs,
            "travel_style": profile.travel_style or "normal",
        }
