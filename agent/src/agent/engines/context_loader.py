"""Context Loader —— 用户画像加载。

从 UserProfileRepositoryPort 查询用户画像（偏好向量、家庭画像、旅行节奏），
增强 IntentSchema 为 EnrichedIntent。

注入模式（推荐）:
  loader = ContextLoader(user_profile_repo=repo)
  → 通过 repo.get_profile(user_id) 获取画像

兜底模式（无 repo）:
  loader = ContextLoader()
  → 直接返回默认画像，不查 DB

输入: IntentSchema + user_id
输出: EnrichedIntent (含 profile_vector, family_profile, historical_rejections)

Author: SnapTrip Team
Date: 2026-05-13 / DI refactor 2026-05-21
"""

from __future__ import annotations

import logging
import uuid

from snaptrip_shared.schemas.plan import EnrichedIntent, IntentSchema

from agent.protocol import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger(__name__)

_DEFAULT_VECTOR = [0.1] * 1536
_DEFAULT_FAMILY: dict = {"child_age": None, "diet": "无偏好", "allergens": []}


class ContextLoader(BaseAgent):
    name = "context_loader"

    def __init__(self, user_profile_repo=None):
        """注入 UserProfileRepositoryPort。

        Args:
            user_profile_repo: 可选。实现 get_profile(user_id) -> dict | None 的端口。
                               为 None 时使用默认画像（不查 DB）。
        """
        super().__init__()
        self._user_profile_repo = user_profile_repo

    async def execute(self, context: AgentContext) -> AgentResult:
        intent_data = context.history[-1].data.get("intent", {}) if context.history else {}
        intent = IntentSchema(**intent_data) if intent_data else IntentSchema()

        uid = self._parse_user_id(context.user_id)
        enriched = await self._load_profile(uid, intent) if uid else self._default(intent, context.user_id)

        return AgentResult(data={"enriched_intent": enriched.model_dump()})

    # ------------------------------------------------------------------
    # profile loading
    # ------------------------------------------------------------------

    async def _load_profile(self, user_id: uuid.UUID, intent: IntentSchema) -> EnrichedIntent:
        if self._user_profile_repo is None:
            return self._default(intent, str(user_id))

        try:
            profile = await self._user_profile_repo.get_profile(str(user_id))
        except Exception:
            logger.warning("context_loader_repo_failed user_id=%s", str(user_id), exc_info=True)
            return self._default(intent, str(user_id))

        if profile is None:
            return self._default(intent, str(user_id))

        historical_rejections: list[str] = []
        prefs = profile.get("preferences", _DEFAULT_FAMILY)
        if isinstance(prefs, dict):
            rejects = prefs.get("historical_rejections", [])
            if isinstance(rejects, list):
                historical_rejections = rejects
        return EnrichedIntent(
            intent=intent,
            profile_vector=profile.get("preference_embedding") or _DEFAULT_VECTOR,
            family_profile=prefs,
            historical_rejections=historical_rejections,
            preferred_pace=profile.get("travel_style") or "normal",
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
