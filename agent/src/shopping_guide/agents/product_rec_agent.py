"""ProductRecAgent — multi-strategy recall + LLM re-ranking.

Two-stage recommendation:
  1. Recall: multi-strategy (keyword search + personalised recommendations + home feed)
  2. Re-rank: LLM-based with user profile context, category diversity, price fit

Adapted from refer/multi-agent-ecommerce-system/python/agents/product_rec_agent.py
"""

from __future__ import annotations

import json
import logging
from typing import Any

from shopping_guide.agents.base_agent import BaseAgent
from shopping_guide.config.settings import get_shopping_guide_settings
from shopping_guide.models.schemas import Product, ProductRecResult, UserProfile

logger = logging.getLogger(__name__)

RERANK_PROMPT = """你是电商推荐排序专家。根据用户画像和候选商品,重新排序并选出最优的{num_items}个商品。

用户画像:
{user_profile}

候选商品:
{candidates}

排序原则:
1. 用户偏好类目优先
2. 价格在用户可接受范围内
3. 保证类目多样性(相邻商品尽量不同类目)
4. 高库存商品优先
5. 新品/热销适当加权

请输出商品ID列表(JSON数组),按推荐优先级排序:
["product_id_1", "product_id_2", ...]

只输出JSON数组,不要其他内容。"""


class ProductRecAgent(BaseAgent):
    """Two-stage product recommendation: recall → LLM re-rank.

    Phase 1 (recall): keyword search + personalised recommendations
    Phase 2 (re-rank): LLM-based contextual re-ranking with user profile

    Receives LLM adapter and HTTP client via constructor injection.
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        http_client: Any = None,
        recall_service: Any = None,
        query_understanding: Any = None,
    ):
        settings = get_shopping_guide_settings()
        super().__init__(
            name="product_rec",
            timeout=settings.sg_agent_timeout_product_rec,
        )
        self.llm = llm_adapter
        self.http = http_client
        self.recall_service = recall_service
        self.query_understanding = query_understanding
        self.model_alias = settings.sg_llm_model_rerank
        self.temperature = settings.sg_llm_temperature_rerank
        self.max_tokens = settings.sg_llm_max_tokens_rerank
        self.max_candidates = settings.sg_max_candidates

    async def _execute(self, **kwargs: Any) -> ProductRecResult:
        user_profile: UserProfile | None = kwargs.get("user_profile")
        num_items: int = kwargs.get("num_items", 10)
        query: str = kwargs.get("query", "")
        scene: str = kwargs.get("scene", "homepage")
        products: list[Product] | None = kwargs.get("products")

        # Phase 1: Multi-strategy recall (skip if pre-recalled products provided)
        if products:
            candidates = list(products)
        else:
            candidates = await self._recall(user_profile, query, scene, num_items * 3)
        logger.info(
            "product_rec.recall total=%d query=%s scene=%s",
            len(candidates),
            query,
            scene,
        )

        # Phase 2: LLM re-rank (only if we have candidates and profile)
        if candidates and len(candidates) > 1:
            ranked_ids = await self._rerank(user_profile, candidates, num_items)
        else:
            ranked_ids = [p.product_id for p in candidates[:num_items]]

        id_to_product = {p.product_id: p for p in candidates}
        final_products: list[Product] = []
        for pid in ranked_ids:
            if pid in id_to_product:
                final_products.append(id_to_product[pid])

        # Fill gaps with unranked candidates
        if len(final_products) < num_items:
            for p in candidates:
                if p.product_id not in ranked_ids:
                    final_products.append(p)
                    if len(final_products) >= num_items:
                        break

        return ProductRecResult(
            success=True,
            products=final_products[:num_items],
            recall_strategy="search+recommendations+homefeed",
            data={
                "candidate_count": len(candidates),
                "reranked": len(ranked_ids),
                "final_count": len(final_products),
            },
            confidence=0.8,
        )

    # ── Recall ────────────────────────────────────────────────────────────────

    async def _recall(
        self,
        profile: UserProfile | None,
        query: str,
        scene: str,
        limit: int,
    ) -> list[Product]:
        """Multi-strategy recall.

        Priority: RecallService (direct) → HTTP API (fallback).

        Channels used via RecallService: es + vector + trending (CF when user has history)
        """
        candidates: dict[str, Product] = {}

        # ── Direct RecallService (preferred) ──
        if self.recall_service and query:
            try:
                filters: dict = {}
                if profile and profile.preferred_categories:
                    filters["preferred_categories"] = profile.preferred_categories
                if profile and profile.price_range:
                    filters["min_price"] = profile.price_range[0]
                    filters["max_price"] = profile.price_range[1]

                # Query understanding: rewrite + pre-computed embedding
                recall_query = query
                pre_embedding: list[float] | None = None
                if self.query_understanding:
                    try:
                        qu_result = await self.query_understanding.understand(
                            query, with_embedding=True, with_expansion=False
                        )
                        if qu_result.rewritten_query and qu_result.rewritten_query != query:
                            recall_query = qu_result.rewritten_query
                            logger.debug("product_rec: query rewritten: %s → %s", query, recall_query)
                        pre_embedding = qu_result.embedding
                    except Exception as exc:
                        logger.debug("product_rec: query_understanding failed: %s", exc)

                recalled = await self.recall_service.recall(
                    query=recall_query,
                    user_id=profile.user_id if profile else None,
                    embedding=pre_embedding,
                    filters=filters,
                    channels=["es", "vector", "trending"],
                    budget=min(limit * 3, self.max_candidates),
                )
                for item in recalled:
                    p = self._normalize_product(item)
                    candidates[p.product_id] = p
                logger.info(
                    "product_rec: RecallService returned %d candidates for query=%s",
                    len(candidates),
                    query,
                )
            except Exception as exc:
                logger.warning("product_rec: RecallService failed, falling back to HTTP: %s", exc)

        # ── HTTP fallback (keyword search) ──
        if not candidates and query and self.http:
            try:
                result = await self.http.get(
                    "/api/v1/portal/products",
                    params={"keyword": query, "page_size": min(limit, 20), "sort_by": "default"},
                    timeout=6.0,
                )
                for item in result.get("items", []):
                    p = self._normalize_product(item)
                    candidates[p.product_id] = p
            except Exception as exc:
                logger.warning("product_rec: search API failed: %s", exc)

        # ── HTTP fallback (browse all) ──
        if self.http and len(candidates) < limit:
            try:
                result = await self.http.get(
                    "/api/v1/portal/products",
                    params={"page_size": min(limit, 20), "sort_by": "default"},
                    timeout=6.0,
                )
                for item in result.get("items", []):
                    p = self._normalize_product(item)
                    if p.product_id not in candidates:
                        candidates[p.product_id] = p
            except Exception as exc:
                logger.warning("product_rec: browse API failed: %s", exc)

        # Sort: preferred categories first, then by stock > 0, then by sale_count
        product_list = list(candidates.values())
        if profile and profile.preferred_categories:
            preferred = set(profile.preferred_categories)
            product_list.sort(
                key=lambda p: (
                    p.category_name in preferred or p.category in preferred,
                    p.stock > 0,
                    p.sale_count,
                ),
                reverse=True,
            )
        else:
            product_list.sort(key=lambda p: (p.stock > 0, p.sale_count), reverse=True)

        return product_list[: min(limit, self.max_candidates)]

    # ── Re-rank ───────────────────────────────────────────────────────────────

    async def _rerank(
        self,
        profile: UserProfile | None,
        candidates: list[Product],
        num_items: int,
    ) -> list[str]:
        """LLM-based re-ranking with user profile context."""
        if not self.llm:
            return [p.product_id for p in candidates[:num_items]]

        if not profile:
            return [p.product_id for p in candidates[:num_items]]

        profile_summary = {
            "segments": [s.value for s in profile.segments],
            "preferred_categories": profile.preferred_categories,
            "preferred_brands": profile.preferred_brands,
            "price_range": list(profile.price_range),
        }
        candidate_summary = [
            {
                "id": p.product_id,
                "name": p.name,
                "category": p.category_name or p.category,
                "price": p.price,
                "brand": p.brand_name or p.brand,
                "stock": p.stock,
                "sale_count": p.sale_count,
                "tags": p.tags,
                "score": p.score,
            }
            for p in candidates
        ]
        prompt = RERANK_PROMPT.format(
            num_items=num_items,
            user_profile=json.dumps(profile_summary, ensure_ascii=False),
            candidates=json.dumps(candidate_summary, ensure_ascii=False),
        )

        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": "你是电商推荐排序专家。"},
                    {"role": "user", "content": prompt},
                ],
                model_alias=self.model_alias,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                enable_thinking=False,
            )
            raw = (response.content or "").strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else raw
            return json.loads(raw)
        except (json.JSONDecodeError, IndexError, Exception) as exc:
            logger.warning("product_rec: LLM rerank failed, fallback to default order: %s", exc)
            return [p.product_id for p in candidates[:num_items]]

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_product(item: dict[str, Any]) -> Product:
        """Normalize a product dict from various backend API shapes into a Product."""
        product_id = str(item.get("product_id") or item.get("id", ""))
        return Product(
            product_id=product_id,
            name=str(item.get("name", "")),
            category=str(item.get("category") or item.get("category_id", "")),
            category_name=str(item.get("category_name") or item.get("category_id", "")),
            price=float(item.get("price", 0) or 0),
            original_price=float(item.get("original_price", 0) or 0),
            description=str(item.get("description", "") or "")[:200],
            brand=str(item.get("brand", "")),
            brand_name=str(item.get("brand_name", "")),
            seller_id=str(item.get("seller_id", "")),
            stock=int(item.get("stock", 0) or 0),
            sale_count=int(item.get("sale_count", 0) or 0),
            tags=list(item.get("tags", []) or []),
            score=float(item.get("score", 0) or 0),
            image_url=str(item.get("image_url", "") or ""),
            images=list(item.get("images", []) or [])[:3],
            marketing_copy=str(item.get("marketing_copy", "")),
        )
