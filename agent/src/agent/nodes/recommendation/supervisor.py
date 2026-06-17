"""RecommendationSupervisor —— 推荐编排器。

三阶段并行编排:
  Phase 1: asyncio.gather(UserProfileAgent, ProductRecAgent[recall_only])
  Phase 2: asyncio.gather(ProductRecAgent[rerank], InventoryAgent)
  Phase 3: MarketingCopyAgent (依赖 Phase 2 结果, 串行)

单个 Agent 失败不影响整体 (degraded fallback)。
返回 RecommendationResponse。

参考 multi-agent-ecommerce-system 的 SupervisorOrchestrator 模式。
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from agent.nodes.recommendation.base import AgentResult, BaseRecommendationAgent
from agent.nodes.recommendation.inventory import InventoryAgent
from agent.nodes.recommendation.marketing_copy import MarketingCopyAgent
from agent.nodes.recommendation.product_rec import ProductRecAgent
from agent.nodes.recommendation.user_profile import UserProfileAgent
from agent.schemas.recommendation import (
    AgentResultItem,
    RecommendationProduct,
    RecommendationRequest,
    RecommendationResponse,
)

logger = logging.getLogger(__name__)


class RecommendationSupervisor:
    """推荐 Supervisor —— 编排 4 个 Agent 的并行/串行执行。

    用法:
        supervisor = RecommendationSupervisor(
            llm_adapter=adapter,
            db_factory=async_session_factory,
            feature_service=feature_svc,
            es_client=es_client,
        )
        response = await supervisor.recommend(request)
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        db_factory: Any = None,
        feature_service: Any = None,
        es_client: Any = None,
        ab_engine: Any = None,
    ) -> None:
        self._llm = llm_adapter
        self._db_factory = db_factory
        self._feature_service = feature_service
        self._es = es_client
        self._ab_engine = ab_engine

        # 初始化 Agent 实例
        self._user_profile_agent = UserProfileAgent(
            llm_adapter=llm_adapter,
            feature_service=feature_service,
        )
        self._product_rec_agent = ProductRecAgent(
            llm_adapter=llm_adapter,
            db_session_factory=db_factory,
            es_client=es_client,
        )
        self._inventory_agent = InventoryAgent(db_session_factory=db_factory)
        self._marketing_copy_agent = MarketingCopyAgent(llm_adapter=llm_adapter)

    async def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        """执行完整推荐流水线。"""
        t0 = time.perf_counter()
        request_id = str(uuid.uuid4())

        agent_results: dict[str, AgentResultItem] = {}

        # A/B 测试分桶
        experiment_group = "control"
        if self._ab_engine and request.user_id:
            try:
                experiment_group = self._ab_engine.assign(request.user_id, "rec_strategy")
            except Exception:
                pass

        user_profile: dict | None = None
        raw_products: list[dict] = []
        final_products: list[RecommendationProduct] = []
        copies: list[dict] = []

        # ═══ Phase 1: 并行 — UserProfile + ProductRec (recall) ═══
        phase1_user_profile: AgentResult | None = None
        phase1_recall: AgentResult | None = None

        tasks_p1 = [
            self._user_profile_agent.run(
                user_id=request.user_id and uuid.UUID(request.user_id),
            ),
            self._product_rec_agent.run(
                num_items=request.num_items,
                recall_only=True,
                scene=request.scene.value if hasattr(request.scene, 'value') else request.scene,
            ),
        ]
        phase1_results = await asyncio.gather(*tasks_p1, return_exceptions=True)

        for i, result in enumerate(phase1_results):
            agent_name = ["user_profile", "product_rec"][i]
            if isinstance(result, AgentResult):
                agent_results[agent_name] = self._to_item(result)
                if agent_name == "user_profile" and result.success:
                    phase1_user_profile = result
                    user_profile = result.data.get("profile")
                elif agent_name == "product_rec" and result.success:
                    phase1_recall = result
                    raw_products = result.data.get("products", [])
            else:
                agent_results[agent_name] = AgentResultItem(
                    agent_name=agent_name, success=False, error=str(result)
                )

        # ═══ Phase 2: 并行 — ProductRec (rerank) + Inventory ═══
        phase2_rerank: AgentResult | None = None
        phase2_inventory: AgentResult | None = None

        if raw_products:
            tasks_p2 = [
                self._product_rec_agent.run(
                    user_profile=user_profile,
                    products=raw_products,
                    num_items=request.num_items,
                    recall_only=False,
                    scene=request.scene.value if hasattr(request.scene, 'value') else request.scene,
                ),
                self._inventory_agent.run(products=raw_products),
            ]
            phase2_results = await asyncio.gather(*tasks_p2, return_exceptions=True)

            for i, result in enumerate(phase2_results):
                agent_name = ["product_rec", "inventory"][i]
                if isinstance(result, AgentResult):
                    agent_results[agent_name] = self._to_item(result)
                    if agent_name == "product_rec" and result.success:
                        phase2_rerank = result
                    elif agent_name == "inventory" and result.success:
                        phase2_inventory = result
                else:
                    agent_results[agent_name] = AgentResultItem(
                        agent_name=agent_name, success=False, error=str(result)
                    )

        # 合并 Phase 2 结果
        if phase2_rerank and phase2_rerank.success:
            ranked_products = phase2_rerank.data.get("products", raw_products)
        else:
            ranked_products = raw_products

        if phase2_inventory and phase2_inventory.success:
            available_ids = {
                p.get("product_id") for p in phase2_inventory.data.get("available_products", [])
            }
            ranked_products = [p for p in ranked_products if p.get("product_id") in available_ids]

        # ═══ Phase 3: 串行 — MarketingCopy (15s 超时防 LLM 卡死) ═══
        if ranked_products:
            try:
                copy_result = await asyncio.wait_for(
                    self._marketing_copy_agent.run(
                        user_profile=user_profile,
                        products=ranked_products,
                    ),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                logger.warning("MarketingCopyAgent timed out after 15s, proceeding without copies")
                copy_result = None
            except Exception as exc:
                logger.warning("MarketingCopyAgent failed: %s", exc)
                copy_result = None

            if isinstance(copy_result, AgentResult):
                agent_results["marketing_copy"] = self._to_item(copy_result)
                if copy_result.success:
                    copies = copy_result.data.get("copies", [])

        # ═══ 组装响应 ═══
        # 合并文案到商品
        copy_map = {c.get("product_id", ""): c.get("copy", "") for c in copies}
        final_products = [
            RecommendationProduct(
                product_id=p.get("product_id", ""),
                name=p.get("name", ""),
                category_id=p.get("category_id", ""),
                price=p.get("price", 0.0),
                brand_name=p.get("brand_name", ""),
                image_url=p.get("image_url", ""),
                sale_count=p.get("sale_count", 0),
                stock=p.get("stock", 0),
                score=p.get("score", 0.0),
                marketing_copy=copy_map.get(p.get("product_id", ""), ""),
            )
            for p in ranked_products[:request.num_items]
        ]

        total_latency_ms = (time.perf_counter() - t0) * 1000

        return RecommendationResponse(
            request_id=request_id,
            user_id=request.user_id,
            session_id=request.session_id,
            products=final_products,
            copies=copies,
            experiment_group=experiment_group,
            agent_results=agent_results,
            total_latency_ms=total_latency_ms,
        )

    @staticmethod
    def _to_item(result: AgentResult) -> AgentResultItem:
        return AgentResultItem(
            agent_name=result.agent_name,
            success=result.success,
            latency_ms=result.latency_ms,
            confidence=result.confidence,
            error=result.error,
        )
