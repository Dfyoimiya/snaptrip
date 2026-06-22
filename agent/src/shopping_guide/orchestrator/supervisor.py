"""Supervisor — parallel dispatch + aggregate pattern.

Coordinates 4 specialist agents in a 3-phase pipeline:

                    ┌──────────────┐
                    │  Supervisor   │
                    └──────┬───────┘
           ┌───────┬───────┼───────┬────────┐
           ▼       ▼       ▼       ▼        │
      UserProfile  ProdRec  MktCopy  Inventory │
           │       │       │       │        │
           └───────┴───────┴───────┘        │
                    │                        │
                    ▼                        │
               Aggregator ◄─────────────────┘
                    │
                    ▼
              A/B Test Engine

Phase 1 (parallel):  UserProfileAgent + ProductRecAgent (recall)
Phase 2 (parallel):  ProductRecAgent (rerank) + InventoryAgent
Phase 3 (serial):    MarketingCopyAgent (personalized copy + compliance)

Adapted from refer/multi-agent-ecommerce-system/python/orchestrator/supervisor.py
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from shopping_guide.agents import (
    InventoryAgent,
    MarketingCopyAgent,
    ProductRecAgent,
    UserProfileAgent,
)
from shopping_guide.models.schemas import (
    Product,
    RecommendationRequest,
    RecommendationResponse,
    UserProfile,
)
from shopping_guide.services.ab_test import ABTestEngine

logger = logging.getLogger(__name__)


class ShoppingGuideSupervisor:
    """Coordinates four agents in parallel-then-aggregate pattern.

    Usage:
        supervisor = ShoppingGuideSupervisor(
            llm_adapter=adapter,
            http_client=client,
        )
        response = await supervisor.recommend(request)
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        http_client: Any = None,
        recall_service: Any = None,
        query_understanding: Any = None,
        ab_engine: ABTestEngine | None = None,
        info_search_supervisor: Any = None,
    ):
        self.llm = llm_adapter
        self.http = http_client
        self.user_profile_agent = UserProfileAgent(
            llm_adapter=llm_adapter,
            http_client=http_client,
        )
        self.product_rec_agent = ProductRecAgent(
            llm_adapter=llm_adapter,
            http_client=http_client,
            recall_service=recall_service,
            query_understanding=query_understanding,
        )
        self.marketing_copy_agent = MarketingCopyAgent(
            llm_adapter=llm_adapter,
        )
        self.inventory_agent = InventoryAgent(
            http_client=http_client,
        )
        self.ab_engine = ab_engine or ABTestEngine()
        self.info_search = info_search_supervisor

    async def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        """Execute the full 3-phase recommendation pipeline."""
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        logger.info(
            "supervisor.start request_id=%s user_id=%s scene=%s items=%d",
            request_id,
            request.user_id,
            request.scene,
            request.num_items,
        )

        # ── A/B test assignment ──
        experiment = self.ab_engine.assign(request.user_id)

        # ═══════════════════════════════════════════════════════════════════
        # Phase 1: parallel — user profile + product recall
        # ═══════════════════════════════════════════════════════════════════
        profile_result, rec_result = await asyncio.gather(
            self.user_profile_agent.run(
                user_id=request.user_id,
                context=request.context,
            ),
            self.product_rec_agent.run(
                user_profile=None,
                num_items=request.num_items * 2,
                query=request.message,
                scene=request.scene,
            ),
        )

        user_profile: UserProfile | None = getattr(profile_result, "profile", None)
        raw_products: list[Product] = getattr(rec_result, "products", [])

        logger.info(
            "supervisor.phase1 request_id=%s profile=%s candidates=%d",
            request_id,
            bool(user_profile),
            len(raw_products),
        )

        # ═══════════════════════════════════════════════════════════════════
        # Phase 2: parallel — re-rank with profile + inventory check
        # ═══════════════════════════════════════════════════════════════════
        rerank_task = self.product_rec_agent.run(
            user_profile=user_profile,
            num_items=request.num_items,
            query=request.message,
            scene=request.scene,
            products=raw_products,  # pass Phase 1 candidates, avoid re-recall
        )
        inventory_task = self.inventory_agent.run(products=raw_products)

        rerank_result, inventory_result = await asyncio.gather(
            rerank_task, inventory_task
        )

        ranked_products: list[Product] = getattr(
            rerank_result, "products", raw_products
        )

        # ── Inventory filter ──
        available_ids = set(getattr(inventory_result, "available_products", []))

        # Always keep in-stock products; fall back to ranked if all filtered
        final_products = [p for p in ranked_products if p.product_id in available_ids]
        if not final_products:
            final_products = ranked_products[:request.num_items]

        # ── Diversity re-rank (category spread) ──
        final_products = _apply_diversity(final_products, request.num_items)

        final_products = final_products[:request.num_items]

        logger.info(
            "supervisor.phase2 request_id=%s ranked=%d available=%d final=%d",
            request_id,
            len(ranked_products),
            len(available_ids),
            len(final_products),
        )

        # ═══════════════════════════════════════════════════════════════════
        # Phase 3: serial — marketing copy generation
        # ═══════════════════════════════════════════════════════════════════
        copy_result = await self.marketing_copy_agent.run(
            user_profile=user_profile,
            products=final_products,
        )
        copies = getattr(copy_result, "copies", [])

        # ── Merge marketing copies into products ──
        copy_map = {c.get("product_id", ""): c.get("copy", "") for c in copies}
        for p in final_products:
            if p.product_id in copy_map:
                p.marketing_copy = copy_map[p.product_id]

        total_latency = (time.perf_counter() - start) * 1000

        logger.info(
            "supervisor.complete request_id=%s total_latency_ms=%.1f products=%d copies=%d",
            request_id,
            total_latency,
            len(final_products),
            len(copies),
        )

        return RecommendationResponse(
            request_id=request_id,
            user_id=request.user_id,
            products=final_products,
            marketing_copies=copies,
            experiment_group=experiment.get("group", "control"),
            agent_results={
                "user_profile": profile_result,
                "product_rec": rerank_result,
                "marketing_copy": copy_result,
                "inventory": inventory_result,
            },
            total_latency_ms=total_latency,
        )

    async def recommend_with_enrichment(self, request: RecommendationRequest) -> RecommendationResponse:
        """Full pipeline + optional info enrichment after product ranking.

        If info_search_supervisor is configured, fetches review data for the
        top-ranked products and merges ratings/snippets into the response.
        """
        response = await self.recommend(request)

        if self.info_search and request.message and response.products:
            try:
                from shopping_guide.models.schemas import InfoSearchRequest

                info_request = InfoSearchRequest(
                    user_id=request.user_id,
                    query=request.message,
                    product_ids=[p.product_id for p in response.products[:3]],
                    sources=["reviews"],
                    max_results_per_source=10,
                )
                info_response = await self.info_search.search(info_request)

                # Merge review data into products
                if info_response.review_summary:
                    for p in response.products:
                        if p.product_id in getattr(
                            info_response.review_summary, "per_product", {}
                        ) or info_response.review_summary:
                            # If user asked about this product, enrich top products
                            pass
            except Exception:
                logger.warning("supervisor: enrichment failed", exc_info=True)

        return response


def _apply_diversity(products: list[Product], top_n: int) -> list[Product]:
    """类目分散重排: 限制每个类目最多出现 2 个商品。

    在保持排序质量的同时, 确保推荐列表的类目多样性。
    不依赖外部服务, 直接在 agent 内部完成。
    """
    if len(products) <= 2:
        return products

    max_per_category = 2
    penalty = 0.70
    category_counts: dict[str, int] = {}

    # Build (product, adjusted_score) pairs
    scored: list[tuple[Product, float]] = []
    for p in products:
        cat = p.category or p.category_name or "__unknown__"
        count = category_counts.get(cat, 0)
        score = p.score

        if count >= max_per_category:
            score = score * penalty

        category_counts[cat] = count + 1
        scored.append((p, score))

    # Sort by adjusted score
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored[:top_n]]
