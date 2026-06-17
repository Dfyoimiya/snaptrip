"""MarketingCopyAgent —— 营销文案生成 Agent。

基于用户分群选择文案模板, LLM 生成个性化推荐文案, 广告法合规过滤。

5 种分群模板:
  - NEW_USER: 温暖欢迎型
  - HIGH_VALUE: 尊享品质型
  - PRICE_SENSITIVE: 超值优惠型
  - ACTIVE: 场景驱动型
  - CHURN_RISK: 召回紧迫型

参考 multi-agent-ecommerce-system 的 MarketingCopyAgent 模板驱动模式。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from agent.nodes.recommendation.base import AgentResult, BaseRecommendationAgent

logger = logging.getLogger(__name__)

# ── 广告法禁用词 (合规过滤) ──
FORBIDDEN_WORDS = re.compile(
    r"最好|第一|国家级|全球首[发款]|绝对|100%|永久|万能|祖传|纯天然"
    r"|顶级|极品|第一品牌|独一无二|冠军|王牌|销量[第冠]"
)

# ── 分群文案模板 (System Prompt) ──
TEMPLATES: dict[str, str] = {
    "NEW_USER": """你是一个温暖的电商导购。用户是新用户, 第一次浏览我们的平台。
请用热情欢迎的语气, 为以下商品生成简短的个性化推荐文案。
强调"首次购物专属体验"和"新品尝鲜"。
每个商品生成 1 句推荐语, 20-40字。""",

    "HIGH_VALUE": """你是一个高端电商顾问。用户是高价值客户, 追求品质生活。
请用优雅、尊享的语气, 为以下商品生成简短的个性化推荐文案。
强调"精选品质"、"专属好物"和"品位之选"。
每个商品生成 1 句推荐语, 15-30字。""",

    "PRICE_SENSITIVE": """你是一个实惠导购专家。用户对价格敏感, 追求性价比。
请用超值、划算的语气, 为以下商品生成简短的个性化推荐文案。
强调"超值好价"、"限时优惠"和"性价比之选"。
每个商品生成 1 句推荐语, 15-30字。""",

    "ACTIVE": """你是一个会生活的好友。用户活跃且乐于探索新品。
请用轻松、活泼的语气, 为以下商品生成简短的个性化推荐文案。
强调"发现好物"、"值得一试"和场景化使用体验。
每个商品生成 1 句推荐语, 15-30字。""",

    "CHURN_RISK": """你是一个贴心的老朋友。用户很久没来了, 我们在召唤ta回来。
请用亲切、怀念的语气, 为以下商品生成简短的个性化推荐文案。
强调"好久不见"、"为你精选"和"特别推荐"。
每个商品生成 1 句推荐语, 15-30字。""",
}

COPY_OUTPUT_INSTRUCTION = """
只输出 JSON 数组, 格式:
[{"product_id": "xxx", "copy": "推荐文案内容"}]
不要输出其他内容。"""


class MarketingCopyAgent(BaseRecommendationAgent):
    """营销文案生成 Agent。"""

    agent_name = "marketing_copy"
    max_retries = 2
    timeout = 12.0

    def __init__(self, llm_adapter: Any = None) -> None:
        super().__init__()
        self._llm = llm_adapter

    async def _execute(self, **kwargs: Any) -> AgentResult:
        user_profile = kwargs.get("user_profile")
        products = kwargs.get("products", [])

        if not products:
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                data={"copies": [], "prompt_template_used": "none"},
                confidence=1.0,
            )

        # 1. 选择模板
        template_key = self._select_template(user_profile) if user_profile else "NEW_USER"
        system_prompt = TEMPLATES.get(template_key, TEMPLATES["NEW_USER"]) + COPY_OUTPUT_INSTRUCTION

        # 2. LLM 生成文案
        if self._llm:
            try:
                copies = await self._generate_with_llm(system_prompt, products)
            except Exception as exc:
                logger.warning("%s: LLM generation failed: %s", self.agent_name, exc)
                copies = self._fallback_copies(products)
        else:
            copies = self._fallback_copies(products)

        # 3. 合规过滤
        copies = [self._compliance_check(c) for c in copies]

        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            data={
                "copies": copies,
                "prompt_template_used": template_key,
            },
            confidence=0.9 if self._llm else 0.6,
        )

    async def _generate_with_llm(self, system_prompt: str, products: list[dict]) -> list[dict]:
        """LLM 生成文案。"""
        product_info = json.dumps(
            [{k: v for k, v in p.items() if k in ("product_id", "name", "price", "brand_name", "category_id")}
             for p in products],
            ensure_ascii=False,
            indent=2,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"为以下商品生成推荐文案:\n{product_info}"},
        ]
        response = await self._llm.chat(
            messages=messages,
            temperature=0.9,
            max_tokens=1024,
        )
        content = response.content if hasattr(response, "content") else str(response)
        return self._parse_copies(content, products)

    def _parse_copies(self, raw: str, products: list[dict]) -> list[dict]:
        """解析 LLM 输出的文案 JSON 数组。"""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        try:
            copies = json.loads(text.strip())
            return copies if isinstance(copies, list) else []
        except json.JSONDecodeError:
            logger.warning("%s: failed to parse copies as JSON", self.agent_name)
            return self._fallback_copies(products)

    @staticmethod
    def _select_template(profile: dict) -> str:
        """根据用户分群选择文案模板。"""
        segments = profile.get("segments", [])
        if isinstance(segments, str):
            segments = [segments]
        # 优先级: NEW_USER > HIGH_VALUE > CHURN_RISK > PRICE_SENSITIVE > ACTIVE
        priority = ["NEW_USER", "HIGH_VALUE", "CHURN_RISK", "PRICE_SENSITIVE", "ACTIVE"]
        for seg in priority:
            if seg in segments:
                return seg
        return "NEW_USER"

    @staticmethod
    def _compliance_check(copy_item: dict) -> dict:
        """广告法合规过滤: 替换禁用词为 ***。"""
        copy_text = copy_item.get("copy", "")
        cleaned = FORBIDDEN_WORDS.sub("***", copy_text)
        return {**copy_item, "copy": cleaned}

    @staticmethod
    def _fallback_copies(products: list[dict]) -> list[dict]:
        """降级兜底: 基于模板关键词生成简单文案。"""
        return [
            {
                "product_id": p.get("product_id", ""),
                "copy": f"为你推荐 {p.get('name', '精选好物')}",
            }
            for p in products
        ]
