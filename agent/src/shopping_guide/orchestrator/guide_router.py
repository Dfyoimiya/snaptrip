"""GuideRouter — intent classification + routing for the shopping guide agent.

The shopping guide has 3 response modes:
  - FAQ: Simple Q&A, direct LLM response
  - PRODUCT_SEARCH: Product recommendations (ShoppingGuideSupervisor)
  - INFO_SEARCH: Information search with web + reviews (InfoSearchSupervisor)

When mode="auto", the router uses LLM to classify intent and dispatch.

Author: SnapTrip Team
Date: 2026-06-23
"""

from __future__ import annotations

import json
import logging
from typing import Any

from shopping_guide.models.schemas import (
    GuideIntent,
    InfoSearchRequest,
    InfoSearchResponse,
    RecommendationRequest,
    RecommendationResponse,
    RoutedRequest,
)

logger = logging.getLogger(__name__)

INTENT_PROMPT = """将用户的购物咨询消息分类为以下三种意图之一:

- faq: 简单问答、政策咨询、操作指导 (如 "怎么退货"、"运费多少")
- product_search: 搜索商品、寻求推荐 (如 "推荐一款降噪耳机"、"有什么好的蓝牙音箱")
- info_search: 查询商品评价、是否值得买、评测对比、避坑 (如 "索尼XM6怎么样"、"这个值不值得买"、"MacBook和ThinkPad哪个好")

用户消息: __QUERY__

请只输出 JSON:
{{"intent": "faq|product_search|info_search", "reason": "简短理由"}}"""


class GuideRouter:
    """Top-level router for the shopping guide agent.

    Classifies user intent and dispatches to the appropriate pipeline:
      - FAQ → direct LLM response
      - Product Search → ShoppingGuideSupervisor.recommend()
      - Info Search → InfoSearchSupervisor.search()

    Usage:
        router = GuideRouter(
            llm_adapter=adapter,
            shopping_supervisor=shopping_supervisor,
            info_search_supervisor=info_search_supervisor,
        )
        response = await router.route(request)
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        shopping_supervisor: Any = None,
        info_search_supervisor: Any = None,
    ):
        self.llm = llm_adapter
        self.shopping_supervisor = shopping_supervisor
        self.info_search_supervisor = info_search_supervisor

    async def route(self, request: RoutedRequest) -> dict[str, Any]:
        """Classify intent (if needed) and dispatch to the correct pipeline.

        Returns a dict with shape:
          {"mode": str, "intent": str, "data": ...}
        """
        # Determine intent
        if request.mode != "auto" and request.mode in ("faq", "product_search", "info_search"):
            intent = GuideIntent(request.mode)
        else:
            intent = await self._classify_intent(request.query)

        logger.info("guide_router: query=%s intent=%s", request.query[:60], intent.value)

        # Dispatch
        if intent == GuideIntent.FAQ:
            return await self._handle_faq(request)
        elif intent == GuideIntent.PRODUCT_SEARCH:
            return await self._handle_product_search(request)
        elif intent == GuideIntent.INFO_SEARCH:
            return await self._handle_info_search(request)
        else:
            return {"mode": "faq", "intent": intent.value, "data": {"answer": "抱歉，我无法理解您的需求。"}}

    # ── Intent Classification ──────────────────────────────────────────────

    async def _classify_intent(self, query: str) -> GuideIntent:
        """LLM-based intent classification."""
        if not self.llm:
            return self._rule_classify(query)

        try:
            prompt = INTENT_PROMPT.replace("__QUERY__", query)
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": "你是意图分类专家，只输出JSON。"},
                    {"role": "user", "content": prompt},
                ],
                model_alias="qwen3.6-flash",
                temperature=0.1,
                max_tokens=128,
                enable_thinking=False,
            )
            raw = (response.content or "").strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1]) if len(lines) > 2 and lines[-1].strip() == "```" else raw
            result = json.loads(raw)
            intent_str = result.get("intent", "faq")
            return GuideIntent(intent_str)
        except Exception:
            logger.debug("guide_router: intent classification failed, falling back to rules", exc_info=True)
            return self._rule_classify(query)

    @staticmethod
    def _rule_classify(query: str) -> GuideIntent:
        """Rule-based intent classification fallback."""
        q = query.strip().lower()

        info_keywords = [
            "怎么样", "好不好", "值不值得", "评测", "口碑", "评价",
            "对比", "区别", "避坑", "缺点", "优缺点", "推荐吗",
        ]
        product_keywords = [
            "推荐", "有什么", "哪些", "有没有", "帮我找", "搜",
            "买个", "哪个好", "性价比",
        ]

        for kw in info_keywords:
            if kw in q:
                return GuideIntent.INFO_SEARCH
        for kw in product_keywords:
            if kw in q:
                return GuideIntent.PRODUCT_SEARCH

        return GuideIntent.FAQ

    # ── Handlers ───────────────────────────────────────────────────────────

    async def _handle_faq(self, request: RoutedRequest) -> dict[str, Any]:
        """Handle FAQ with direct LLM response."""
        answer = "抱歉，我暂时无法处理这个问题。"  # default

        if self.llm:
            try:
                response = await self.llm.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": "你是SnapTrip商城的智能导购助手，用中文回答用户问题，简洁明了。",
                        },
                        {"role": "user", "content": request.query},
                    ],
                    model_alias="qwen3.6-flash",
                    temperature=0.5,
                    max_tokens=512,
                    enable_thinking=False,
                )
                answer = (response.content or "").strip()
            except Exception:
                logger.warning("guide_router: FAQ LLM call failed", exc_info=True)

        return {"mode": "faq", "intent": "faq", "data": {"answer": answer}}

    async def _handle_product_search(self, request: RoutedRequest) -> dict[str, Any]:
        """Handle product search via ShoppingGuideSupervisor."""
        if not self.shopping_supervisor:
            return {"mode": "product_search", "intent": "product_search", "data": {"products": []}}

        try:
            rec_request = RecommendationRequest(
                user_id=request.user_id,
                message=request.query,
                scene="search",
                num_items=10,
                context=request.context,
            )
            response: RecommendationResponse = await self.shopping_supervisor.recommend(rec_request)
            return {
                "mode": "product_search",
                "intent": "product_search",
                "data": response.model_dump(mode="json"),
            }
        except Exception as exc:
            logger.error("guide_router: product search failed: %s", exc)
            return {"mode": "product_search", "intent": "product_search", "data": {"products": []}}

    async def _handle_info_search(self, request: RoutedRequest) -> dict[str, Any]:
        """Handle info search via InfoSearchSupervisor."""
        if not self.info_search_supervisor:
            return {"mode": "info_search", "intent": "info_search", "data": {}}

        try:
            info_request = InfoSearchRequest(
                user_id=request.user_id,
                query=request.query,
                product_ids=request.product_ids,
                sources=["web", "reviews"],
                max_results_per_source=5,
                context=request.context,
            )
            response: InfoSearchResponse = await self.info_search_supervisor.search(info_request)
            return {
                "mode": "info_search",
                "intent": "info_search",
                "data": response.model_dump(mode="json"),
            }
        except Exception as exc:
            logger.error("guide_router: info search failed: %s", exc)
            return {"mode": "info_search", "intent": "info_search", "data": {}}
