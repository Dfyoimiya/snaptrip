"""UserProfileAgent —— 用户画像分析 Agent。

从 FeatureService 获取行为数据, 通过 LLM 分析生成用户画像。

输出 JSON 画像:
  - segments: [NEW_USER, ACTIVE, HIGH_VALUE, PRICE_SENSITIVE, CHURN_RISK]
  - preferred_categories: 类目偏好列表
  - price_range: [min, max]
  - rfm_score: {recency, frequency, monetary}
  - real_time_tags: 实时行为标签

参考 multi-agent-ecommerce-system 的 UserProfileAgent 模式。
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from agent.nodes.recommendation.base import AgentResult, BaseRecommendationAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个电商用户画像分析师。根据提供的用户行为数据, 分析用户特征并输出 JSON。

输出 JSON 格式:
{
  "segments": ["NEW_USER" | "ACTIVE" | "HIGH_VALUE" | "PRICE_SENSITIVE" | "CHURN_RISK"],
  "preferred_categories": ["category_id_1", ...],
  "price_range": [min_price, max_price],
  "rfm_score": {"recency": 0.0-1.0, "frequency": 0.0-1.0, "monetary": 0.0-1.0},
  "real_time_tags": {"intent": "browsing"|"buying"|"comparing", "engagement": "low"|"medium"|"high"}
}

分类规则:
- NEW_USER: 无购买记录, 浏览<10次 → 新用户
- ACTIVE: 近期浏览>5次/小时, 有加购行为 → 活跃用户
- HIGH_VALUE: RFM monetary>0.7, 订单>3 → 高价值用户
- PRICE_SENSITIVE: 收藏多但未购买, 浏览价格排序 → 价格敏感
- CHURN_RISK: 超过30天无浏览无购买 → 流失风险

只输出 JSON, 不要其他内容。"""


class UserProfileAgent(BaseRecommendationAgent):
    """用户画像分析 Agent。"""

    agent_name = "user_profile"
    max_retries = 2
    timeout = 8.0

    def __init__(self, llm_adapter: Any = None, feature_service: Any = None) -> None:
        super().__init__()
        self._llm = llm_adapter
        self._feature_service = feature_service

    async def _execute(self, **kwargs: Any) -> AgentResult:
        user_id = kwargs.get("user_id")
        if not user_id:
            return AgentResult.failed(self.agent_name, "missing user_id")

        # 1. 获取特征数据
        features: dict = {}
        if self._feature_service and isinstance(user_id, uuid.UUID):
            try:
                features = await self._feature_service.get_user_features(user_id)
            except Exception as exc:
                logger.warning("%s: feature_service failed: %s", self.agent_name, exc)
                features = self._build_fallback_features(user_id)

        # 2. LLM 分析
        if self._llm:
            try:
                profile = await self._analyze_with_llm(features)
            except Exception as exc:
                logger.warning("%s: LLM analysis failed, using rule-based: %s", self.agent_name, exc)
                profile = self._rule_based_profile(features)
        else:
            profile = self._rule_based_profile(features)

        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            data={"profile": profile, "features": features},
            confidence=0.85 if self._llm else 0.7,
        )

    async def _analyze_with_llm(self, features: dict) -> dict:
        """调用 LLM 分析用户特征 → 画像 JSON。"""
        human_msg = f"用户行为数据:\n{json.dumps(features, ensure_ascii=False, indent=2)}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": human_msg},
        ]
        response = await self._llm.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=512,
        )
        content = response.content if hasattr(response, "content") else str(response)
        return self._parse_profile(content)

    def _parse_profile(self, raw: str) -> dict:
        """解析 LLM 输出的 JSON 画像。"""
        # 去除可能的 markdown 代码块标记
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            logger.warning("%s: failed to parse LLM output as JSON, using fallback", self.agent_name)
            return self._rule_based_profile({})

    def _rule_based_profile(self, features: dict) -> dict:
        """规则兜底: 无 LLM 时的确定性画像生成。"""
        rt = features.get("real_time", {})
        fav = features.get("favorites", {})
        ph = features.get("purchase_history", {})
        rfm = ph.get("rfm", {})

        views_24h = rt.get("views_24h", 0)
        purchases_7d = rt.get("purchases_7d", 0)
        total_orders = ph.get("total_orders", 0)
        monetary = rfm.get("monetary", 0)
        recency = rfm.get("recency", 0)

        # 分类逻辑
        segments = []
        if total_orders == 0 and views_24h < 10:
            segments.append("NEW_USER")
        elif recency < 0.1 and views_24h == 0:
            segments.append("CHURN_RISK")
        elif purchases_7d > 0:
            segments.append("ACTIVE")
            if monetary > 0.7 and total_orders > 3:
                segments.append("HIGH_VALUE")
        elif fav.get("count", 0) > 5:
            segments.append("PRICE_SENSITIVE")
        else:
            segments.append("ACTIVE")

        return {
            "segments": segments or ["NEW_USER"],
            "preferred_categories": fav.get("category_ids", []),
            "price_range": [0.0, 1000.0],
            "rfm_score": rfm,
            "real_time_tags": {
                "intent": "buying" if purchases_7d > 0 else ("browsing" if views_24h > 5 else "comparing"),
                "engagement": "high" if views_24h > 20 else ("medium" if views_24h > 5 else "low"),
            },
        }

    @staticmethod
    def _build_fallback_features(user_id: Any) -> dict:
        return {
            "user_id": str(user_id),
            "real_time": {"views_1h": 0, "views_24h": 0, "clicks_1h": 0, "searches_1h": 0, "purchases_7d": 0},
            "favorites": {"count": 0, "category_ids": [], "recent_product_ids": []},
            "purchase_history": {"total_orders": 0, "rfm": {"recency": 0, "frequency": 0, "monetary": 0}, "recent_category_ids": [], "avg_order_amount": 0},
        }
