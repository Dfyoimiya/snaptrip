"""ReviewSearchAgent — internal review database search + aggregation.

Responsibilities:
  - Accept product_ids or resolve query to product_ids via product search API
  - Fetch review stats + top reviews for each product in parallel
  - Aggregate ratings, extract key themes via LLM
  - Return per-product ReviewSummary for downstream synthesis

Author: SnapTrip Team
Date: 2026-06-23
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from shopping_guide.agents.base_agent import BaseAgent
from shopping_guide.config.settings import get_shopping_guide_settings
from shopping_guide.models.schemas import ReviewItem, ReviewSearchAgentResult, ReviewSummary

logger = logging.getLogger(__name__)

THEME_EXTRACTION_PROMPT = """根据以下用户评价，提取2-3个最常见的关键主题（如"降噪效果"、"佩戴舒适度"、"续航"），每个主题不超过6个字。

评价内容:
__REVIEWS_TEXT__

只输出JSON数组，不要其他内容:
["主题1", "主题2", "主题3"]"""


class ReviewSearchAgent(BaseAgent):
    """Search internal review database via backend portal API.

    Fetches review statistics and top reviews for target products.
    Uses LLM for optional theme extraction from review content.

    Constructor injection:
      - http_client: MarketplaceClient for backend API calls
      - llm_adapter: For theme extraction
    """

    def __init__(
        self,
        http_client: Any = None,
        llm_adapter: Any = None,
    ):
        settings = get_shopping_guide_settings()
        super().__init__(
            name="review_search",
            timeout=settings.sg_agent_timeout_review_search,
            max_retries=settings.sg_agent_max_retries_review_search,
        )
        self.http = http_client
        self.llm = llm_adapter
        self.max_per_product = settings.sg_review_search_max_per_product
        self.model_alias = getattr(settings, "sg_llm_model", "qwen3.6-flash")

    async def _execute(self, **kwargs: Any) -> ReviewSearchAgentResult:
        product_ids: list[str] = kwargs.get("product_ids", [])
        query: str = kwargs.get("query", "")
        max_reviews: int = kwargs.get("max_reviews", 20)

        # 1. Resolve product_ids from query if not explicitly given
        if not product_ids and query:
            product_ids = await self._resolve_products(query)
        if not product_ids:
            return ReviewSearchAgentResult(
                success=True,
                confidence=0.1,
                data={"reason": "no product_ids to search"},
            )

        # 2. Parallel: fetch stats + reviews for each product
        per_product: dict[str, ReviewSummary] = {}
        total_scanned = 0

        tasks = [self._fetch_product_reviews(pid, max_reviews) for pid in product_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for pid, result in zip(product_ids, results):
            if isinstance(result, ReviewSummary):
                per_product[pid] = result
                total_scanned += result.total_count
            else:
                logger.warning("review_search: failed for product %s: %s", pid, result)

        # 3. LLM theme extraction (optional, for products with reviews)
        if self.llm:
            for pid, agg in per_product.items():
                if agg.top_reviews:
                    agg.summary_text = await self._extract_themes_and_summarize(agg)

        logger.info(
            "review_search: completed products=%d total_reviews=%d",
            len(per_product),
            total_scanned,
        )

        return ReviewSearchAgentResult(
            success=True,
            per_product=per_product,
            total_scanned=total_scanned,
            data={"product_ids": product_ids},
            confidence=0.85 if per_product else 0.1,
        )

    # ── Product Resolution ──────────────────────────────────────────────────

    async def _resolve_products(self, query: str) -> list[str]:
        """Resolve a natural language query to product IDs via product search API."""
        if not self.http:
            return []

        try:
            result = await self.http.get(
                "/api/v1/portal/products",
                params={"keyword": query, "page_size": 5, "sort_by": "default"},
                timeout=5.0,
            )
            items = result.get("items", [])
            ids = [str(item.get("product_id") or item.get("id", "")) for item in items]
            ids = [pid for pid in ids if pid]
            logger.debug("review_search: resolved query=%s → products=%s", query, ids)
            return ids[:3]  # top 3 matches
        except Exception as exc:
            logger.warning("review_search: product resolution failed: %s", exc)
            return []

    # ── Review Fetching ─────────────────────────────────────────────────────

    async def _fetch_product_reviews(
        self, product_id: str, max_reviews: int
    ) -> ReviewSummary:
        """Fetch review stats + top reviews for a single product.

        Calls two backend APIs in parallel:
          - GET /api/v1/portal/reviews/stats?product_id=...
          - GET /api/v1/portal/reviews?product_id=...&page=1&page_size=...
        """
        if not self.http:
            return ReviewSummary()

        try:
            stats_task = self.http.get(
                "/api/v1/portal/reviews/stats",
                params={"product_id": product_id},
                timeout=4.0,
            )
            list_task = self.http.get(
                "/api/v1/portal/reviews",
                params={"product_id": product_id, "page": 1, "page_size": max_reviews},
                timeout=4.0,
            )

            stats_data, list_data = await asyncio.gather(
                stats_task, list_task, return_exceptions=True
            )
        except Exception as exc:
            logger.warning("review_search: API calls failed for %s: %s", product_id, exc)
            return ReviewSummary()

        # Parse stats
        average_rating = 0.0
        total_count = 0
        try:
            if isinstance(stats_data, dict) and "average_rating" in stats_data:
                average_rating = float(stats_data.get("average_rating", 0))
                total_count = int(stats_data.get("total_count", 0))
        except Exception:
            logger.debug("review_search: stats parse failed for %s", product_id)

        # Parse reviews list
        top_reviews: list[ReviewItem] = []
        try:
            if isinstance(list_data, dict):
                items = list_data.get("items", [])
                # Sort by rating diversity: pick top, middle, and critical reviews for balance
                sorted_items = sorted(
                    items, key=lambda r: (r.get("rating", 0), r.get("created_at", "")), reverse=True
                )
                top_reviews = [
                    ReviewItem(
                        review_id=str(item.get("id", "")),
                        user_name="匿名用户" if item.get("is_anonymous") else str(item.get("user_id", "")[:8] + "***"),
                        rating=int(item.get("rating", 0)),
                        content=str(item.get("content", "") or ""),
                        created_at=str(item.get("created_at", "")),
                    )
                    for item in sorted_items[:4]
                ]
        except Exception:
            logger.debug("review_search: review list parse failed for %s", product_id)

        return ReviewSummary(
            average_rating=average_rating,
            total_count=total_count,
            top_reviews=top_reviews,
        )

    # ── Theme Extraction ────────────────────────────────────────────────────

    async def _extract_themes_and_summarize(self, agg: ReviewSummary) -> str:
        """LLM extracts key themes and generates a summary of reviews.

        Returns a concise summary string (≤80 chars).
        """
        if not self.llm or not agg.top_reviews:
            return self._fallback_summary(agg)

        # Build reviews text for LLM
        reviews_text_parts: list[str] = []
        for r in agg.top_reviews:
            reviews_text_parts.append(f"[{r.rating}星] {r.content}")
        reviews_text = "\n".join(reviews_text_parts)

        try:
            prompt = THEME_EXTRACTION_PROMPT.replace("__REVIEWS_TEXT__", reviews_text[:1500])
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": "你是用户评价分析专家，用中文输出。"},
                    {"role": "user", "content": prompt},
                ],
                model_alias=self.model_alias,
                temperature=0.3,
                max_tokens=200,
                enable_thinking=False,
            )
            raw = (response.content or "").strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1]) if len(lines) > 2 and lines[-1].strip() == "```" else raw
            themes = json.loads(raw)

            if themes:
                themes_str = "、".join(themes[:3])
                return (
                    f"用户普遍关注{themes_str}。"
                    f"综合评分{agg.average_rating}/5（{agg.total_count}条评价）"
                )
        except Exception:
            logger.debug("review_search: theme extraction failed", exc_info=True)

        return self._fallback_summary(agg)

    @staticmethod
    def _fallback_summary(agg: ReviewSummary) -> str:
        if agg.total_count == 0:
            return "暂无用户评价"
        return f"综合评分{agg.average_rating}/5（{agg.total_count}条评价）"
