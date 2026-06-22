"""MarketingCopyAgent — personalised marketing copy + compliance check.

Generates tailored product descriptions based on user segment, with
Chinese Advertising Law compliance filtering.

Adapted from refer/multi-agent-ecommerce-system/python/agents/marketing_copy_agent.py
"""

from __future__ import annotations

import json
import logging

from typing import Any

from shopping_guide.agents.base_agent import BaseAgent
from shopping_guide.config.settings import get_shopping_guide_settings
from shopping_guide.models.schemas import (
    MarketingCopyResult,
    Product,
    UserProfile,
    UserSegment,
)

logger = logging.getLogger(__name__)

PROMPT_TEMPLATES: dict[UserSegment, str] = {
    UserSegment.NEW_USER: """你是电商营销文案专家。为新用户撰写欢迎+推荐文案。
风格要求：热情友好、突出新人专属优惠感、降低决策门槛。
每个商品生成一条文案(30-50字)。""",

    UserSegment.HIGH_VALUE: """你是电商营销文案专家。为高价值VIP用户撰写推荐文案。
风格要求：品质感、尊享感、突出商品高端属性和品牌价值。
每个商品生成一条文案(30-50字)。""",

    UserSegment.PRICE_SENSITIVE: """你是电商营销文案专家。为价格敏感用户撰写推荐文案。
风格要求：突出性价比、促销价格、限时优惠、省钱金额。
每个商品生成一条文案(30-50字)。""",

    UserSegment.ACTIVE: """你是电商营销文案专家。为活跃用户撰写推荐文案。
风格要求：突出商品亮点和使用场景,引发共鸣。
每个商品生成一条文案(30-50字)。""",

    UserSegment.CHURN_RISK: """你是电商营销文案专家。为即将流失的用户撰写召回文案。
风格要求：情感唤回、专属折扣、限时活动、制造紧迫感。
每个商品生成一条文案(30-50字)。""",
}

# Chinese Advertising Law — forbidden absolute/superlative terms
FORBIDDEN_WORDS = [
    "最好", "第一", "国家级", "全球首", "绝对", "100%",
    "永久", "万能", "祖传", "纯天然", "全网最低", "全国第一",
    "顶级", "极品", "最便宜", "销量第一", "独一无二",
]

COPY_OUTPUT_INSTRUCTION = """
请以JSON数组格式输出,每个元素格式:
[{"product_id": "xxx", "copy": "文案内容"}]
只输出JSON,不要其他内容。"""


class MarketingCopyAgent(BaseAgent):
    """Generates personalised marketing copy per user segment with compliance check.

    Receives LLM adapter via constructor injection.
    """

    def __init__(self, llm_adapter: Any = None):
        settings = get_shopping_guide_settings()
        super().__init__(
            name="marketing_copy",
            timeout=settings.sg_agent_timeout_marketing_copy,
        )
        self.llm = llm_adapter
        self.model_alias = settings.sg_llm_model
        self.temperature = settings.sg_llm_temperature_copy
        self.max_tokens = settings.sg_llm_max_tokens_copy

    async def _execute(self, **kwargs: Any) -> MarketingCopyResult:
        user_profile: UserProfile | None = kwargs.get("user_profile")
        products: list[Product] = kwargs.get("products", [])

        if not products:
            return MarketingCopyResult(success=True, copies=[], confidence=1.0)

        if not self.llm:
            return MarketingCopyResult(
                success=True,
                copies=[
                    {"product_id": p.product_id, "copy": p.marketing_copy or p.description[:50]}
                    for p in products
                ],
                prompt_template_used="fallback",
                confidence=0.3,
            )

        template_key = self._select_template(user_profile)
        system_prompt = PROMPT_TEMPLATES[template_key]

        product_lines: list[str] = []
        for p in products:
            tags = ",".join(p.tags) if p.tags else ""
            product_lines.append(
                f"- ID:{p.product_id} 名称:{p.name} 类目:{p.category_name or p.category} "
                f"价格:¥{p.price:.0f} 品牌:{p.brand_name or p.brand} 标签:{tags}"
            )

        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt + COPY_OUTPUT_INSTRUCTION},
                    {"role": "user", "content": "商品列表:\n" + "\n".join(product_lines)},
                ],
                model_alias=self.model_alias,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                enable_thinking=False,
            )
            copies = self._parse_copies(response.content)
        except Exception as exc:
            logger.warning("marketing_copy: LLM failed, fallback to product descriptions: %s", exc)
            copies = [
                {"product_id": p.product_id, "copy": p.description[:50] or p.name}
                for p in products
            ]

        copies = [self._compliance_check(c) for c in copies]

        return MarketingCopyResult(
            success=True,
            copies=copies,
            prompt_template_used=template_key.value,
            confidence=0.9,
        )

    @staticmethod
    def _select_template(profile: UserProfile | None) -> UserSegment:
        """Select the best prompt template based on user segments (priority-ordered)."""
        if not profile or not profile.segments:
            return UserSegment.ACTIVE
        priority = [
            UserSegment.NEW_USER,
            UserSegment.HIGH_VALUE,
            UserSegment.CHURN_RISK,
            UserSegment.PRICE_SENSITIVE,
            UserSegment.ACTIVE,
        ]
        for seg in priority:
            if seg in profile.segments:
                return seg
        return UserSegment.ACTIVE

    @staticmethod
    def _parse_copies(raw: str) -> list[dict[str, str]]:
        """Parse LLM JSON response into copy items, with defensive handling."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else cleaned
            data = json.loads(cleaned)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            return []
        except (json.JSONDecodeError, IndexError):
            return []

    @staticmethod
    def _compliance_check(copy_item: dict[str, str]) -> dict[str, str]:
        """Filter forbidden advertising words per Chinese Advertising Law."""
        text = copy_item.get("copy", "")
        for word in FORBIDDEN_WORDS:
            if word in text:
                text = text.replace(word, "***")
        copy_item["copy"] = text
        return copy_item
