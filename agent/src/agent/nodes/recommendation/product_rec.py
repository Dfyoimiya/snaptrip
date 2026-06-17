"""ProductRecAgent —— 商品推荐 Agent。

两阶段推荐:
  1. 召回 (Recall): 多策略混合
     - ES 全文搜索 (基于用户偏好类目)
     - 协同过滤 (基于收藏夹共现)
     - 热门兜底 (sale_count DESC)
  2. 重排 (Rerank): LLM 基于用户画像对候选排序

参考 multi-agent-ecommerce-system 的 ProductRecAgent 两阶段模式。
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from agent.nodes.recommendation.base import AgentResult, BaseRecommendationAgent

logger = logging.getLogger(__name__)

RERANK_PROMPT = """你是一个电商推荐排序专家。根据用户画像, 从候选商品中选出最适合用户的 {num_items} 个商品, 按推荐优先级排序。

用户画像:
{user_profile}

候选商品:
{candidates}

输出格式: 只输出 JSON 数组, 包含商品ID, 不要其他内容。
示例: ["id1", "id2", "id3"]"""


class ProductRecAgent(BaseRecommendationAgent):
    """商品推荐 Agent —— 召回 + 重排。

    两个模式:
      - recall_only=True: 仅召回, 不重排 (Phase 1)
      - recall_only=False: 传入 profile 进行 LLM 重排 (Phase 2)
    """

    agent_name = "product_rec"
    max_retries = 2
    timeout = 10.0

    def __init__(
        self,
        llm_adapter: Any = None,
        db_session_factory: Any = None,
        es_client: Any = None,
    ) -> None:
        super().__init__()
        self._llm = llm_adapter
        self._db_factory = db_session_factory
        self._es = es_client

    async def _execute(self, **kwargs: Any) -> AgentResult:
        user_profile = kwargs.get("user_profile")
        num_items = kwargs.get("num_items", 10)
        recall_only = kwargs.get("recall_only", False)
        scene = kwargs.get("scene", "homepage")
        passed_products = kwargs.get("products")  # Phase 2: pre-recalled products

        # 1. 召回 (多策略) — 仅在未传入产品时执行
        if passed_products:
            candidates = list(passed_products)
            self._last_recall_strategy = "passed"
        else:
            candidates = await self._recall(user_profile, num_items * 3, scene)

        if recall_only or not candidates:
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                data={
                    "products": candidates[:num_items],
                    "recall_strategy": self._last_recall_strategy,
                    "total_candidates": len(candidates),
                },
                confidence=0.7,
            )

        # 2. 重排 (LLM)
        if self._llm and user_profile:
            try:
                ranked_ids = await self._rerank(user_profile, candidates, num_items)
            except Exception as exc:
                logger.warning("%s: LLM rerank failed, using recall order: %s", self.agent_name, exc)
                ranked_ids = [p.get("product_id", "") for p in candidates[:num_items]]
        else:
            ranked_ids = [p.get("product_id", "") for p in candidates[:num_items]]

        # 按重排顺序组装结果
        id_map = {p.get("product_id", ""): p for p in candidates}
        final_products = [id_map[pid] for pid in ranked_ids if pid in id_map]

        # 如果重排结果不够, 用召回结果补齐
        if len(final_products) < num_items:
            for c in candidates:
                if len(final_products) >= num_items:
                    break
                if c.get("product_id") not in {p.get("product_id") for p in final_products}:
                    final_products.append(c)

        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            data={
                "products": final_products[:num_items],
                "recall_strategy": self._last_recall_strategy,
                "total_candidates": len(candidates),
                "reranked": bool(self._llm and user_profile),
            },
            confidence=0.85 if (self._llm and user_profile) else 0.7,
        )

    async def _recall(
        self, user_profile: dict | None, num_items: int, scene: str,
    ) -> list[dict]:
        """多策略召回: ES语义搜索 + 协同过滤(收藏夹) + 热门兜底。"""
        candidates: list[dict] = []
        self._last_recall_strategy = "hot"

        # 策略1: ES 全文搜索 (基于用户偏好类目)
        if self._es and user_profile:
            preferred = user_profile.get("preferred_categories", [])
            if preferred:
                try:
                    # 用偏好类目名作为搜索词, 取热门商品
                    es_results = await self._es.search(
                        category_ids=preferred,
                        sort_by="sale_count",
                        size=num_items,
                    )
                    for hit in es_results:
                        candidates.append({
                            "product_id": str(hit.get("id", "")),
                            "name": hit.get("name", ""),
                            "category_id": hit.get("category_id", ""),
                            "price": hit.get("price", 0),
                            "sale_count": hit.get("sale_count", 0),
                            "brand_name": hit.get("brand_name", ""),
                            "image_url": hit.get("image_url", ""),
                            "score": 0.8,
                            "_source": "es",
                        })
                    self._last_recall_strategy = "es_preferred"
                except Exception as exc:
                    logger.warning("%s: ES recall failed: %s", self.agent_name, exc)

        # 策略2: 协同过滤 (基于收藏夹共现)
        if self._db_factory and user_profile:
            # TODO: Phase 2 — 完整实现协同过滤
            # 当前使用热门商品 + 类目过滤作为简化版本
            pass

        # 策略3: 热门兜底 (sale_count DESC, 从 DB 查询)
        if len(candidates) < num_items and self._db_factory:
            try:
                db_candidates = await self._recall_from_db(num_items - len(candidates), user_profile)
                # 去重
                existing_ids = {c.get("product_id") for c in candidates}
                for c in db_candidates:
                    if c.get("product_id") not in existing_ids:
                        candidates.append(c)
                if db_candidates:
                    self._last_recall_strategy = "db_hot"
            except Exception as exc:
                logger.warning("%s: DB recall failed: %s", self.agent_name, exc)

        # 策略4: 静态 mock 兜底 (开发/测试用)
        if not candidates:
            candidates = self._mock_products(num_items)
            self._last_recall_strategy = "mock"

        return candidates

    async def _recall_from_db(self, limit: int, user_profile: dict | None = None) -> list[dict]:
        """从 PostgreSQL 查询热门商品。"""
        from sqlalchemy import select

        from app.models.product.product import PmsProduct

        async with self._db_factory() as db:
            stmt = (
                select(PmsProduct)
                .where(
                    PmsProduct.publish_status == 1,
                    PmsProduct.verify_status == 1,
                    PmsProduct.is_deleted.is_(False),
                )
                .order_by(PmsProduct.sale_count.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            products = result.scalars().all()
            return [
                {
                    "product_id": str(p.id),
                    "name": p.name or "",
                    "category_id": str(p.category_id) if p.category_id else "",
                    "price": float(p.price) if p.price else 0,
                    "sale_count": p.sale_count or 0,
                    "brand_name": getattr(p, 'brand_name', '') or '',
                    "image_url": p.default_pic or "",
                    "stock": getattr(p, 'stock', 100) or 100,
                    "publish_status": getattr(p, 'publish_status', 1),
                    "verify_status": getattr(p, 'verify_status', 1),
                    "score": 0.5,
                    "_source": "db",
                }
                for p in products
            ]

    async def _rerank(
        self, user_profile: dict, candidates: list[dict], num_items: int,
    ) -> list[str]:
        """LLM 重排: 根据用户画像对候选排序。"""
        profile_summary = json.dumps(user_profile, ensure_ascii=False, indent=2)
        candidate_summary = json.dumps(
            [{k: v for k, v in c.items() if k != "_source"} for c in candidates],
            ensure_ascii=False,
            indent=2,
        )
        prompt = RERANK_PROMPT.format(
            num_items=num_items,
            user_profile=profile_summary,
            candidates=candidate_summary,
        )
        messages = [
            {"role": "system", "content": "你是一个电商推荐排序专家。只输出 JSON 数组。"},
            {"role": "user", "content": prompt},
        ]
        response = await self._llm.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=512,
        )
        content = response.content if hasattr(response, "content") else str(response)
        return self._parse_ranked_ids(content, num_items)

    def _parse_ranked_ids(self, raw: str, num_items: int) -> list[str]:
        """解析 LLM 输出的商品ID数组。"""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        try:
            ids = json.loads(text.strip())
            return ids[:num_items] if isinstance(ids, list) else []
        except json.JSONDecodeError:
            logger.warning("%s: failed to parse rerank output as JSON array", self.agent_name)
            return []

    @staticmethod
    def _mock_products(num_items: int) -> list[dict]:
        """静态 mock 数据 (开发/测试兜底)。"""
        mock = [
            {"product_id": f"mock-{i:03d}", "name": f"推荐商品 {i}", "category_id": str(uuid.uuid4()),
             "price": 99.0 + i * 50, "sale_count": 1000 - i * 50, "brand_name": "Sample Brand",
             "image_url": "", "score": 0.3, "_source": "mock"}
            for i in range(1, num_items + 1)
        ]
        return mock
