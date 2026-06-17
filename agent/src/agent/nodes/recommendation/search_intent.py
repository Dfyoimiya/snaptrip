"""SearchIntentAgent —— 搜索意图分类。

规则分类 + LLM 兜底, 输出意图类型与对应的融合权重。

意图类型:
  - transactional: 购买意图明确 ("买", "便宜", "折扣", "包邮")
  - navigational:  品类/品牌导航 ("iPhone 15", "Nike 跑鞋")
  - informational: 信息搜集 ("什么", "怎么", "推荐", "排行", "对比")

融合权重:
  | Intent         | BM25 | Vector | CF   | Price | Category |
  |----------------|------|--------|------|-------|----------|
  | transactional  | 0.30 | 0.30   | 0.15 | 0.15  | 0.10     |
  | navigational   | 0.50 | 0.12   | 0.15 | 0.08  | 0.15     |
  | informational  | 0.20 | 0.45   | 0.15 | 0.05  | 0.15     |

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import logging
from typing import Any

from agent.nodes.recommendation.base import AgentResult, BaseRecommendationAgent

logger = logging.getLogger(__name__)

# 意图关键词规则
_TRANSACTIONAL_KEYWORDS = [
    "买", "购", "价格", "便宜", "折扣", "优惠", "促销", "包邮",
    "下单", "现货", "秒杀", "特价", "清仓", "限时", "满减",
    "buy", "cheap", "discount", "sale", "deal", "price",
]
_NAVIGATIONAL_KEYWORDS = [
    "品牌", "官方", "旗舰店", "正品", "专卖",
    "brand", "official", "store",
]
_INFORMATIONAL_KEYWORDS = [
    "什么", "怎么", "如何", "哪个", "推荐", "排行", "对比",
    "测评", "怎么样", "好不好", "值得", "适合", "新手",
    "best", "vs", "compare", "review", "recommend", "top",
    "how", "what", "which", "guide",
]

# 意图权重映射 (ES + vector + CF 三路融合)
# 三路加权: BM25 × w_bm25 + vector_similarity × w_vec + CF_similarity × w_cf
INTENT_WEIGHTS = {
    "transactional": {"bm25": 0.30, "vector": 0.30, "cf": 0.15, "price": 0.15, "category": 0.10},
    "navigational":  {"bm25": 0.50, "vector": 0.12, "cf": 0.15, "price": 0.08, "category": 0.15},
    "informational": {"bm25": 0.20, "vector": 0.45, "cf": 0.15, "price": 0.05, "category": 0.15},
}


class SearchIntentAgent(BaseRecommendationAgent):
    """搜索意图分类 Agent。

    两层策略:
      1. 规则匹配 (快速, 覆盖 80%+ 查询)
      2. LLM 分类 (兜底, 处理模糊查询)
    """

    agent_name = "search_intent"
    max_retries = 1
    timeout = 5.0

    def __init__(self, llm_adapter: Any = None) -> None:
        super().__init__()
        self._llm = llm_adapter

    async def _execute(self, **kwargs: Any) -> AgentResult:
        query: str = (kwargs.get("query") or "").strip().lower()
        if not query:
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                data={"intent": "navigational", "weights": INTENT_WEIGHTS["navigational"]},
                confidence=1.0,
            )

        # 1. 规则匹配
        rule_intent = _classify_by_rules(query)
        if rule_intent:
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                data={"intent": rule_intent, "weights": INTENT_WEIGHTS[rule_intent]},
                confidence=0.85,
            )

        # 2. LLM 兜底
        if self._llm:
            try:
                llm_intent = await self._llm_classify(query)
                return AgentResult(
                    agent_name=self.agent_name,
                    success=True,
                    data={"intent": llm_intent, "weights": INTENT_WEIGHTS[llm_intent]},
                    confidence=0.70,
                )
            except Exception as exc:
                logger.warning("search_intent: LLM classification failed: %s", exc)

        # 3. 默认 navigational
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            data={"intent": "navigational", "weights": INTENT_WEIGHTS["navigational"]},
            confidence=0.50,
        )

    async def _llm_classify(self, query: str) -> str:
        prompt = f"""你是一个电商搜索意图分类器。分析用户搜索词, 返回意图类型。

意图类型:
- transactional: 明确购买意图, 关注价格/折扣/购买
- navigational: 搜索特定品类/品牌/商品
- informational: 信息搜集, 对比, 求推荐

用户搜索词: "{query}"

只回复一个单词: transactional / navigational / informational"""
        messages = [
            {"role": "system", "content": "只回复一个单词: transactional, navigational, 或 informational"},
            {"role": "user", "content": prompt},
        ]
        response = await self._llm.chat(messages=messages, temperature=0.1, max_tokens=16)
        content = (response.content if hasattr(response, "content") else str(response)).strip().lower()
        if content in ("transactional", "navigational", "informational"):
            return content
        return "navigational"


def _classify_by_rules(query: str) -> str | None:
    """规则匹配意图分类, 返回 None 表示无法确定。"""
    t_score = sum(1 for kw in _TRANSACTIONAL_KEYWORDS if kw in query)
    i_score = sum(1 for kw in _INFORMATIONAL_KEYWORDS if kw in query)
    n_score = sum(1 for kw in _NAVIGATIONAL_KEYWORDS if kw in query)

    # 处理重叠: 如果同时匹配多个, 按优先级 informational > transactional > navigational
    if i_score > 0:
        return "informational"
    if t_score > 0:
        return "transactional"
    if n_score > 0:
        return "navigational"

    return None
