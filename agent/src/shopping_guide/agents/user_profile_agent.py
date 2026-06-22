"""UserProfileAgent — analyse user behaviour into structured profile.

Uses LLM to infer user segments, preferred categories, price range, and
RFM scores from behavioural data collected via the marketplace backend.

Adapted from refer/multi-agent-ecommerce-system/python/agents/user_profile_agent.py
"""

from __future__ import annotations

import json
import logging
from typing import Any

from shopping_guide.agents.base_agent import BaseAgent
from shopping_guide.config.settings import get_shopping_guide_settings
from shopping_guide.models.schemas import UserProfile, UserProfileResult, UserSegment

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个电商用户画像分析专家。根据用户的行为数据,分析用户特征并生成画像。

你需要输出以下JSON格式:
{
  "segments": ["new_user"|"active"|"high_value"|"price_sensitive"|"churn_risk"],
  "preferred_categories": ["类目1", "类目2"],
  "preferred_brands": ["品牌1", "品牌2"],
  "price_range": [最低价, 最高价],
  "rfm_score": {"recency": 0-1, "frequency": 0-1, "monetary": 0-1},
  "real_time_tags": {"活跃时段": "...", "偏好风格": "..."}
}

只输出JSON,不要其他内容。"""


class UserProfileAgent(BaseAgent):
    """Analyses user behaviour into structured UserProfile via LLM.

    Receives LLM adapter via constructor injection (not internal ChatOpenAI).
    Behaviour data is collected from marketplace backend or context fallback.
    """

    def __init__(self, llm_adapter: Any = None, http_client: Any = None):
        settings = get_shopping_guide_settings()
        super().__init__(
            name="user_profile",
            timeout=settings.sg_agent_timeout_user_profile,
        )
        self.llm = llm_adapter
        self.http = http_client
        self.model_alias = settings.sg_llm_model
        self.temperature = settings.sg_llm_temperature_profile
        self.max_tokens = settings.sg_llm_max_tokens_profile

    async def _execute(self, **kwargs: Any) -> UserProfileResult:
        user_id: str = kwargs["user_id"]
        context: dict = kwargs.get("context", {})

        behaviour_data = await self._collect_behaviour(user_id, context)

        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"用户ID: {user_id}\n行为数据: {json.dumps(behaviour_data, ensure_ascii=False)}",
                },
            ],
            model_alias=self.model_alias,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            enable_thinking=False,
        )

        profile = self._parse_profile(user_id, response.content)

        return UserProfileResult(
            success=True,
            profile=profile,
            data={"raw_analysis": response.content},
            confidence=0.85,
        )

    async def _collect_behaviour(self, user_id: str, context: dict) -> dict:
        """Collect user behaviour from marketplace backend or context fallback."""
        data: dict[str, Any] = {"user_id": user_id}

        # Try marketplace backend for real user profile
        if self.http:
            try:
                raw = await self.http.get("/api/v1/portal/member/profile", timeout=4.0)
                data.update({
                    "member_profile": raw,
                    "recent_views": raw.get("recent_views", []),
                    "recent_purchases": raw.get("recent_purchases", []),
                })
            except Exception as exc:
                logger.warning("Failed to fetch member profile: %s", exc)

        # Try preferences from cross-session memory
        if self.http:
            try:
                prefs = await self.http.get(
                    f"/api/v1/portal/shopping-guide/preferences/{user_id}",
                    timeout=3.0,
                )
                data["cross_session_prefs"] = prefs
                if not data.get("preferred_categories") and prefs.get("categories"):
                    data["preferred_categories"] = prefs["categories"]
                if not data.get("preferred_brands") and prefs.get("brands"):
                    data["preferred_brands"] = prefs["brands"]
                if not data.get("price_range") and prefs.get("price_range"):
                    data["price_range"] = prefs["price_range"]
            except Exception:
                pass

        # Context fallback for demo / development
        if not data.get("recent_views"):
            data["recent_views"] = context.get("recent_views", [])
        if not data.get("recent_purchases"):
            data["recent_purchases"] = context.get("recent_purchases", [])
        data["view_count_30d"] = context.get("view_count_30d", 0)
        data["purchase_count_90d"] = context.get("purchase_count_90d", 0)
        data["avg_order_amount"] = context.get("avg_order_amount", 0)

        return data

    @staticmethod
    def _parse_profile(user_id: str, raw: str) -> UserProfile:
        """Parse LLM JSON response into UserProfile, with defensive handling."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else cleaned
            data = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            data = {}

        segments: list[UserSegment] = []
        for s in data.get("segments", ["active"]):
            try:
                segments.append(UserSegment(s))
            except ValueError:
                continue

        price_range_raw = data.get("price_range", [0, 10000])
        price_range = (
            float(price_range_raw[0]),
            float(price_range_raw[1]) if len(price_range_raw) > 1 else 10000.0,
        )

        return UserProfile(
            user_id=user_id,
            segments=segments or [UserSegment.ACTIVE],
            preferred_categories=data.get("preferred_categories", []),
            preferred_brands=data.get("preferred_brands", []),
            price_range=price_range,
            rfm_score=data.get("rfm_score", {}),
            real_time_tags=data.get("real_time_tags", {}),
        )
