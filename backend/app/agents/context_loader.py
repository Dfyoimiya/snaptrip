"""Context Loader —— 用户画像加载。

从 PostgreSQL 的 user_profiles 表查询用户画像（偏好向量、家庭画像、旅行节奏），
增强 IntentSchema 为 EnrichedIntent。

查询逻辑:
  1. 从 context 中提取 user_id 和 intent
  2. 查 UserProfile 表（JOIN users），取 preference_embedding / preferences / travel_style
  3. 映射为 EnrichedIntent 字段
  4. 用户不存在时返回默认画像（兜底，不影响链路）

输入: IntentSchema + user_id
输出: EnrichedIntent (含 profile_vector, family_profile, historical_rejections)

Author: SnapTrip Team
Date: 2026-05-13 / DB integration 2026-05-18
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.db.session import AsyncSessionLocal
from app.models.user_profile import UserProfile
from app.schemas.plan import EnrichedIntent, IntentSchema

logger = logging.getLogger(__name__)

_DEFAULT_VECTOR = [0.1] * 1536
_DEFAULT_FAMILY: dict = {"child_age": None, "diet": "无偏好", "allergens": []}


class ContextLoader(BaseAgent):
    name = "context_loader"

    async def execute(self, context: AgentContext) -> AgentResult:
        intent_data = context.history[-1].data.get("intent", {}) if context.history else {}
        intent = IntentSchema(**intent_data) if intent_data else IntentSchema()

        uid = self._parse_user_id(context.user_id)
        enriched = await self._load_profile(uid, intent) if uid else self._default(intent, context.user_id)

        return AgentResult(data={"enriched_intent": enriched.model_dump()})

    # ------------------------------------------------------------------
    # DB
    # ------------------------------------------------------------------

    async def _load_profile(self, user_id: uuid.UUID, intent: IntentSchema) -> EnrichedIntent:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
                profile = result.scalar_one_or_none()
        except Exception:
            logger.warning("context_loader_db_failed", user_id=str(user_id), exc_info=True)  # type: ignore[call-arg]
            return self._default(intent, str(user_id))

        if profile is None:
            return self._default(intent, str(user_id))

        historical_rejections: list[str] = []
        prefs = profile.preferences or _DEFAULT_FAMILY
        if isinstance(prefs, dict):
            rejects = prefs.get("historical_rejections", [])
            if isinstance(rejects, list):
                historical_rejections = rejects
        return EnrichedIntent(
            intent=intent,
            profile_vector=profile.preference_embedding or _DEFAULT_VECTOR,
            family_profile=prefs,
            historical_rejections=historical_rejections,
            preferred_pace=profile.travel_style or "normal",
            user_id=str(user_id),
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _default(self, intent: IntentSchema, user_id: str) -> EnrichedIntent:
        return EnrichedIntent(
            intent=intent,
            profile_vector=_DEFAULT_VECTOR,
            family_profile=_DEFAULT_FAMILY,
            historical_rejections=[],
            preferred_pace="normal",
            user_id=user_id,
        )

    @staticmethod
    def _parse_user_id(raw: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(raw)
        except (ValueError, AttributeError):
            return None
