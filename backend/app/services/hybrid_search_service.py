"""混合搜索服务 —— ES BM25 + pgvector 融合编排。

流程:
  1. 意图分类 → 确定融合权重
  2. 并发执行 ES BM25 + pgvector 向量检索
  3. 分数归一化 + 加权融合
  4. 个性化 boost + 去重 + 排序

降级策略:
  - ES 不可用 → 纯 vector
  - pgvector 不可用 → 纯 ES
  - 两者都不可用 → DB ILIKE (终极兜底)

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product.product import PmsProduct

logger = logging.getLogger(__name__)


class HybridSearchService:
    """ES BM25 + pgvector + CF 混合搜索。

    三路召回 + 加权融合:
      - ES BM25 (关键词匹配)
      - pgvector (语义相似度)
      - CF (协同过滤, 用户级个性化)

    Query Understanding 统一层:
      - 意图分类 → 实体抽取 → 查询改写 → 查询扩展 → 向量化
      - 替代旧的 SearchIntentAgent

    用法:
        svc = HybridSearchService(
            es_client, vector_service, cf_service, db,
            query_understanding=query_understanding_svc,
        )
        result = await svc.search(keyword="手机", min_price=1000, max_price=5000)
    """

    def __init__(
        self,
        es_client=None,
        vector_service=None,
        cf_service=None,
        db: AsyncSession | None = None,
        intent_agent=None,  # deprecated, use query_understanding
        query_understanding=None,
        personalization_service=None,
    ) -> None:
        self._es = es_client
        self._vector = vector_service
        self._cf = cf_service
        self._db = db
        self._intent_agent = intent_agent  # backward compat
        self._query_understanding = query_understanding
        self._personalization = personalization_service

    async def search(
        self,
        keyword: str | None = None,
        category_id: str | None = None,
        brand_id: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort_by: str = "default",
        page: int = 1,
        page_size: int = 20,
        user_id: UUID | str | None = None,
        user_segment: str | None = None,
        diversity_top_n: int = 0,
        match_mode: str = "smart",
    ) -> dict[str, Any]:
        """混合搜索入口。

        Args:
            user_segment: 用户分群 (new_user/active/high_value/price_sensitive/churn_risk)
            diversity_top_n: 对 top-N 应用类目多样性重排 (0=不启用)

        Returns:
            {"items": [...], "total": int, "page": int, "page_size": int,
             "intent": str | None, "method": str}
        """
        normalized_keyword = keyword.strip() if keyword else None

        # C 端普通商品搜索使用严格包含匹配，确保只返回字段中含关键词的商品。
        if normalized_keyword and match_mode == "contains" and self._db:
            db_items, db_total = await self._db_ilike_fallback(
                keyword=normalized_keyword,
                category_id=category_id,
                brand_id=brand_id,
                min_price=min_price,
                max_price=max_price,
                sort_by=sort_by,
                page=page,
                page_size=page_size,
            )
            return {
                "items": db_items,
                "total": db_total,
                "page": page,
                "page_size": page_size,
                "intent": "exact_contains",
                "method": "db_contains",
            }

        # 无关键词 → 纯分类/价格筛选 (不需要向量检索)
        if not keyword:
            return await self._filter_only(
                category_id=category_id,
                brand_id=brand_id,
                min_price=min_price,
                max_price=max_price,
                sort_by=sort_by,
                page=page,
                page_size=page_size,
            )

        # 1. Query Understanding (意图 + 实体 + 改写 + 向量化)
        intent = "navigational"
        # 默认权重已对齐 ES + ik_max_word 中文分词精度提升
        weights = {"bm25": 0.60, "vector": 0.05, "cf": 0.05, "price": 0.05, "category": 0.10, "brand": 0.15}
        rewritten_keyword = keyword
        pre_embedding: list[float] | None = None
        extracted_entities: dict = {}

        if self._query_understanding:
            try:
                qu_result = await self._query_understanding.understand(
                    keyword,
                    with_embedding=True,
                    with_expansion=False,
                )
                intent = qu_result.intent
                weights = dict(qu_result.weights)
                extracted_entities = qu_result.entities.__dict__ if qu_result.entities else {}
                if qu_result.rewritten_query and qu_result.rewritten_query != keyword:
                    rewritten_keyword = qu_result.rewritten_query
                    logger.debug("hybrid_search: query rewritten: %s → %s", keyword, rewritten_keyword)
                pre_embedding = qu_result.embedding
                logger.debug(
                    "hybrid_search: query_understanding intent=%s entities=%s confidence=%.2f",
                    intent,
                    {k: v for k, v in extracted_entities.items() if v},
                    qu_result.confidence,
                )
            except Exception as exc:
                logger.debug("hybrid_search: query_understanding failed: %s", exc)
        elif self._intent_agent:
            # Fallback: old SearchIntentAgent (deprecated)
            try:
                result = await self._intent_agent.run(query=keyword)
                if result.success and result.data:
                    intent = result.data.get("intent", "navigational")
                    weights = result.data.get("weights", weights)
            except Exception as exc:
                logger.debug("hybrid_search: intent classification failed: %s", exc)

        # 1.5 分群感知权重调整
        if user_segment:
            from app.services.fusion_weight_service import apply_segment_weights

            weights = apply_segment_weights(weights, user_segment)

        # Apply extracted entity hints (only if not explicitly provided)
        # Brand name → used as fusion boost (not hard filter, to tolerate LLM extraction errors)
        extracted_brand: str | None = None
        if extracted_entities:
            if min_price is None and extracted_entities.get("price_min"):
                min_price = _safe_float(extracted_entities["price_min"])
            if max_price is None and extracted_entities.get("price_max"):
                max_price = _safe_float(extracted_entities["price_max"])
            extracted_brand = extracted_entities.get("brand") or None

        # 2. 并发召回 (ES + vector + CF)
        # Use rewritten query for ES, pre-computed embedding for vector
        es_future = self._es_recall(
            rewritten_keyword, category_id, brand_id, min_price, max_price, sort_by, page, page_size * 3
        )
        vec_future = self._vector_recall(keyword, category_id, page_size * 3, embedding=pre_embedding)
        cf_future = self._cf_recall(user_id, page_size * 2)

        es_results, vec_results, cf_results = await asyncio.gather(
            es_future,
            vec_future,
            cf_future,
            return_exceptions=True,
        )
        if isinstance(es_results, Exception):
            logger.debug("hybrid_search: ES recall failed: %s", es_results)
            es_results = []
        if isinstance(vec_results, Exception):
            logger.debug("hybrid_search: vector recall failed: %s", vec_results)
            vec_results = []
        if isinstance(cf_results, Exception):
            logger.debug("hybrid_search: CF recall failed: %s", cf_results)
            cf_results = []

        # 3. 为 CF 独有结果补全商品详情
        if cf_results:
            es_vec_ids = {str(r.get("id", r.get("product_id", ""))) for r in es_results + vec_results}
            cf_only = [r for r in cf_results if r.get("product_id", "") not in es_vec_ids]
            if cf_only:
                cf_filled = await self._fill_cf_details(cf_only)
                # 将 CF 独有结果视为 vector 源加入融合 (由 _cf_norm 驱动)
                vec_results = list(vec_results) + cf_filled

        # 4. 分数融合 (5 权重: bm25 + vector + cf + price + category)
        fused = self._fuse_scores(
            es_results, vec_results, cf_results, weights,
            category_id=category_id,
            user_avg_price=None,  # populated by personalization layer if available
            extracted_brand=extracted_brand,
        )

        # 4. 个性化 boost
        if self._personalization and user_id:
            try:
                fused = await self._personalization.boost(fused, user_id)
            except Exception as exc:
                logger.debug("hybrid_search: personalization boost failed: %s", exc)

        # 5. 价格后过滤 (vector 召回不做价格过滤, 在此统一处理)
        if min_price is not None or max_price is not None:
            fused = [
                p
                for p in fused
                if (min_price is None or p.get("price", 0) >= min_price)
                and (max_price is None or p.get("price", 0) <= max_price)
            ]

        # 6. 品牌后过滤
        if brand_id:
            fused = [p for p in fused if str(p.get("brand_id", "")) == str(brand_id)]

        # 7. 兜底: ES + vector 都没结果 → DB ILIKE
        if not fused and self._db:
            logger.debug("hybrid_search: ES + vector empty, falling back to DB ILIKE")
            db_items, db_total = await self._db_ilike_fallback(
                keyword=keyword,
                category_id=category_id,
                brand_id=brand_id,
                min_price=min_price,
                max_price=max_price,
                sort_by=sort_by,
                page=page,
                page_size=page_size,
            )
            return {
                "items": db_items,
                "total": db_total,
                "page": page,
                "page_size": page_size,
                "intent": intent,
                "method": "db_fallback",
            }

        # 8. 排序 + 多样性重排 + 分页
        fused = self._apply_sort(fused, sort_by)

        # 多样性重排 (仅对首页 top-N 生效)
        if diversity_top_n > 0 and page == 1 and len(fused) > diversity_top_n:
            try:
                from app.services.diversity_service import DiversityService

                fused = DiversityService.apply_category_spread(
                    fused,
                    top_n=max(diversity_top_n, page_size * 2),
                    min_categories=3,
                    max_per_category=2,
                )
                logger.debug("hybrid_search: diversity applied, top_n=%d", diversity_top_n)
            except Exception as exc:
                logger.debug("hybrid_search: diversity re-rank failed: %s", exc)

        total = len(fused)
        start = (page - 1) * page_size
        items = fused[start : start + page_size]

        method = (
            "hybrid"
            if (es_results and vec_results)
            else ("es_only" if es_results else "vector_only" if vec_results else "db_fallback")
        )
        if cf_results and method != "db_fallback":
            method = "hybrid_cf" if method == "hybrid" else method + "_cf"

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "intent": intent,
            "method": method,
        }

    # ── 召回 ──

    async def _es_recall(
        self,
        keyword: str,
        category_id: str | None,
        brand_id: str | None,
        min_price: float | None,
        max_price: float | None,
        sort_by: str,
        page: int,
        size: int,
    ) -> list[dict]:
        if not self._es:
            return []
        raw = await self._es.search_products(
            keyword=keyword,
            category_id=category_id,
            brand_id=brand_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            page=page,
            page_size=size,
        )
        items = raw.get("items", [])
        for item in items:
            item["_source"] = "es"
            item.setdefault("score", 0.0)
            # 将 es 返回的 score (可为 None) 归一化
            if item["score"] is None:
                item["score"] = 0.0
        return items

    async def _vector_recall(
        self,
        keyword: str,
        category_id: str | None,
        limit: int,
        embedding: list[float] | None = None,
    ) -> list[dict]:
        if not self._vector:
            return []
        try:
            if embedding is None:
                embedding = await self._get_query_embedding(keyword)
            if not embedding:
                return []
            results = await self._vector.search_by_text_embedding(
                embedding,
                limit=limit,
                category_id=category_id,
            )
            for r in results:
                r["_source"] = "vector"
            return results
        except Exception as exc:
            logger.debug("hybrid_search: vector recall error: %s", exc)
            return []

    async def _cf_recall(
        self,
        user_id: UUID | str | None,
        limit: int,
    ) -> list[dict]:
        """协同过滤召回 (仅登录用户)。"""
        if not self._cf or not user_id:
            return []
        try:
            results = await self._cf.recommend(user_id, n=limit)
            for r in results:
                r["_source"] = "cf"
            return results
        except Exception as exc:
            logger.debug("hybrid_search: CF recall error: %s", exc)
            return []

    async def _fill_cf_details(self, cf_results: list[dict]) -> list[dict]:
        """为 CF 独有结果补充商品详情 (name/price/image等)。"""
        if not cf_results or not self._db:
            return cf_results

        cf_ids = [r.get("product_id", "") for r in cf_results if r.get("product_id")]
        if not cf_ids:
            return cf_results

        from uuid import UUID as _UUID

        result = await self._db.execute(
            select(PmsProduct).where(
                PmsProduct.id.in_([_UUID(pid) for pid in cf_ids]),
                PmsProduct.publish_status == 1,
                PmsProduct.is_deleted.is_(False),
            )
        )
        products = {str(p.id): p for p in result.scalars().all()}

        filled = []
        for r in cf_results:
            pid = r.get("product_id", "")
            p = products.get(pid)
            if p:
                filled.append(
                    {
                        "id": pid,
                        "product_id": pid,
                        "name": p.name or "",
                        "price": float(p.price) if p.price else 0,
                        "sale_count": p.sale_count or 0,
                        "image_url": p.default_pic or "",
                        "brand_name": getattr(p, "brand_name", "") or "",
                        "category_id": str(p.category_id) if p.category_id else "",
                        "stock": getattr(p, "stock", 100) or 100,
                        "score": r.get("score", 0),
                        "_source": "cf",
                    }
                )
        return filled

    async def _get_query_embedding(self, query: str) -> list[float] | None:
        """获取查询文本的 embedding (384-dim)。

        策略: 本地 sentence-transformers (优先) → LiteLLM (兜底)。
        """
        # 优先: 本地 sentence-transformers
        try:

            model = _get_local_embedding_model()
            embedding = await asyncio.to_thread(model.encode, query, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as exc:
            logger.debug("hybrid_search: local embedding failed: %s", exc)

        # 兜底: LiteLLM proxy
        try:
            import openai

            from app.core.config import commerce_settings

            client = openai.AsyncOpenAI(
                base_url=f"{commerce_settings.LITELLM_BASE_URL}/v1",
                api_key=commerce_settings.LITELLM_API_KEY or "sk-litellm",
            )
            resp = await client.embeddings.create(
                model="text-embedding-3-small",
                input=query,
            )
            return resp.data[0].embedding
        except Exception as exc:
            logger.debug("hybrid_search: embedding generation failed: %s", exc)
            return None

    # ── 融合 ──

    def _fuse_scores(
        self,
        es_results: list[dict],
        vec_results: list[dict],
        cf_results: list[dict],
        weights: dict[str, float],
        category_id: str | None = None,
        user_avg_price: float | None = None,
        extracted_brand: str | None = None,
    ) -> list[dict]:
        """三路分数归一化 + 六权重加权融合。

        final_score = ES_norm × w_bm25 + vector_norm × w_vec + CF_norm × w_cf
                    + price_fit × w_price + category_match × w_category
                    + brand_match × w_brand

        price_fit:  1 - |price - user_avg_price| / max(user_avg_price, price)
                    (falls back to batch-internal price normalization)
        category_match: 1.0 if product matches requested category_id, else 0.3
        brand_match: 1.0 if product brand matches extracted brand (substring),
                     0.5 if no brand extracted (neutral),
                     0.1 if brand extracted but doesn't match (penalty)
        """
        w_bm25 = weights.get("bm25", 0.50)
        w_vec = weights.get("vector", 0.12)
        w_cf = weights.get("cf", 0.15)
        w_price = weights.get("price", 0.05)
        w_category = weights.get("category", 0.10)
        w_brand = weights.get("brand", 0.00)

        # 归一化 ES 分数
        es_scores = [r.get("score", 0.0) or 0.0 for r in es_results]
        es_max = max(es_scores) if es_scores else 1.0
        es_min = min(es_scores) if es_scores else 0.0
        es_range = max(es_max - es_min, 0.001)

        for r in es_results:
            raw = r.get("score", 0.0) or 0.0
            r["_norm_score"] = (raw - es_min) / es_range

        # 归一化 vector 分数
        vec_scores = [r.get("score", 0.0) or 0.0 for r in vec_results]
        vec_max = max(vec_scores) if vec_scores else 1.0
        vec_min = min(vec_scores) if vec_scores else 0.0
        vec_range = max(vec_max - vec_min, 0.001)

        for r in vec_results:
            raw = r.get("score", 0.0) or 0.0
            r["_norm_score"] = (raw - vec_min) / vec_range

        # 归一化 CF 分数
        cf_scores = [r.get("score", 0.0) or 0.0 for r in cf_results]
        cf_max = max(cf_scores) if cf_scores else 1.0
        cf_min = min(cf_scores) if cf_scores else 0.0
        cf_range = max(cf_max - cf_min, 0.001)

        for r in cf_results:
            raw = r.get("score", 0.0) or 0.0
            r["_norm_score"] = (raw - cf_min) / cf_range

        # 合并 → id → {norm scores, _sources}
        merged: dict[str, dict] = {}
        for r in es_results:
            pid = str(r.get("id", r.get("product_id", "")))
            if not pid:
                continue
            merged[pid] = {
                **r,
                "product_id": pid,
                "name": r.get("name", ""),
                "price": self._to_float(r.get("price", 0)),
                "sale_count": r.get("sale_count", 0) or 0,
                "image_url": r.get("image_url", r.get("default_pic", "")),
                "brand_name": r.get("brand_name", ""),
                "category_id": str(r.get("category_id", "")),
                "stock": r.get("stock", 0) or 0,
                "_sources": ["es"],
                "_es_norm": r.get("_norm_score", 0),
                "_vec_norm": 0.0,
                "_cf_norm": 0.0,
                "_price_fit": 0.0,
                "_category_match": 0.0,
                "_brand_match": 0.0,
            }

        for r in vec_results:
            pid = str(r.get("product_id", ""))
            if not pid:
                continue
            if pid in merged:
                merged[pid]["_sources"].append("vector")
                merged[pid]["_vec_norm"] = r.get("_norm_score", 0)
            else:
                merged[pid] = {
                    **r,
                    "product_id": pid,
                    "name": r.get("name", ""),
                    "price": self._to_float(r.get("price", 0)),
                    "sale_count": r.get("sale_count", 0) or 0,
                    "image_url": r.get("image_url", r.get("default_pic", "")),
                    "brand_name": r.get("brand_name", ""),
                    "category_id": str(r.get("category_id", "")),
                    "stock": r.get("stock", 0) or 0,
                    "_sources": ["vector"],
                    "_es_norm": 0.0,
                    "_vec_norm": r.get("_norm_score", 0),
                    "_cf_norm": 0.0,
                    "_price_fit": 0.0,
                    "_category_match": 0.0,
                    "_brand_match": 0.0,
                }

        # CF 结果 (标记来源但不重复计 vector_norm)
        for r in cf_results:
            pid = str(r.get("product_id", ""))
            if not pid:
                continue
            if pid in merged:
                merged[pid]["_sources"].append("cf")
                merged[pid]["_cf_norm"] = r.get("_norm_score", 0)
            else:
                merged[pid] = {
                    **r,
                    "product_id": pid,
                    "name": r.get("name", ""),
                    "price": self._to_float(r.get("price", 0)),
                    "sale_count": r.get("sale_count", 0) or 0,
                    "image_url": r.get("image_url", r.get("default_pic", "")),
                    "brand_name": r.get("brand_name", ""),
                    "category_id": str(r.get("category_id", "")),
                    "stock": r.get("stock", 0) or 0,
                    "_sources": ["cf"],
                    "_es_norm": 0.0,
                    "_vec_norm": 0.0,
                    "_cf_norm": r.get("_norm_score", 0),
                    "_price_fit": 0.0,
                    "_category_match": 0.0,
                    "_brand_match": 0.0,
                }

        # ── Compute price_fit & category_match for all merged items ──
        all_prices = [
            item.get("price", 0)
            for item in merged.values()
            if item.get("price", 0) > 0
        ]
        if all_prices:
            if user_avg_price and user_avg_price > 0:
                # User-aware price fit: closer to user's average spend → higher score
                for item in merged.values():
                    p = item.get("price", 0) or 0
                    item["_price_fit"] = max(
                        0.0,
                        1.0
                        - abs(p - user_avg_price)
                        / max(user_avg_price, p, 1.0),
                    )
            else:
                # Batch-internal price normalization: mid-range prices get higher scores
                median_price = sorted(all_prices)[len(all_prices) // 2]
                max_price = max(all_prices)
                for item in merged.values():
                    p = item.get("price", 0) or 0
                    item["_price_fit"] = max(
                        0.0,
                        1.0
                        - abs(p - median_price)
                        / max(max_price, 1.0),
                    )

        if category_id:
            for item in merged.values():
                item["_category_match"] = (
                    1.0
                    if str(item.get("category_id", "")) == str(category_id)
                    else 0.3
                )

        # Brand match: boost products matching the extracted brand entity
        if extracted_brand:
            eb = extracted_brand.lower()
            for item in merged.values():
                product_brand = (item.get("brand_name", "") or "").lower()
                # Case-insensitive substring match (handles "小米" vs "小米（MI）")
                if eb in product_brand or product_brand in eb:
                    item["_brand_match"] = 1.0
                else:
                    item["_brand_match"] = 0.1  # strong penalty for non-matching brand
        else:
            for item in merged.values():
                item["_brand_match"] = 0.5  # neutral: no brand extracted

        # 计算最终分数 (六路加权)
        for item in merged.values():
            item["score"] = (
                item["_es_norm"] * w_bm25
                + item["_vec_norm"] * w_vec
                + item["_cf_norm"] * w_cf
                + item["_price_fit"] * w_price
                + item["_category_match"] * w_category
                + item["_brand_match"] * w_brand
            )

        result = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)
        return result

    # ── 纯筛选模式 ──

    async def _filter_only(
        self,
        category_id: str | None = None,
        brand_id: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort_by: str = "default",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """无关键词时的纯筛选 + DB 查询。"""
        base = (
            select(PmsProduct)
            .where(PmsProduct.publish_status == 1)
            .where(PmsProduct.verify_status == 1)
            .where(PmsProduct.is_deleted.is_(False))
        )
        count_q = (
            select(func.count(PmsProduct.id))
            .where(PmsProduct.publish_status == 1)
            .where(PmsProduct.verify_status == 1)
            .where(PmsProduct.is_deleted.is_(False))
        )

        if category_id:
            base = base.where(PmsProduct.category_id == category_id)
            count_q = count_q.where(PmsProduct.category_id == category_id)
        if brand_id:
            base = base.where(PmsProduct.brand_id == brand_id)
            count_q = count_q.where(PmsProduct.brand_id == brand_id)
        if min_price is not None:
            base = base.where(PmsProduct.price >= min_price)
            count_q = count_q.where(PmsProduct.price >= min_price)
        if max_price is not None:
            base = base.where(PmsProduct.price <= max_price)
            count_q = count_q.where(PmsProduct.price <= max_price)

        sort_map = {
            "price_asc": PmsProduct.price.asc(),
            "price_desc": PmsProduct.price.desc(),
            "sales": PmsProduct.sale_count.desc(),
            "new": PmsProduct.created_at.desc(),
        }
        order_by = sort_map.get(sort_by, PmsProduct.sale_count.desc())

        result = await self._db.execute(count_q)
        total = result.scalar() or 0

        result = await self._db.execute(base.order_by(order_by).offset((page - 1) * page_size).limit(page_size))
        products = result.scalars().all()

        items = [
            {
                "id": str(p.id),
                "product_id": str(p.id),
                "name": p.name or "",
                "price": float(p.price) if p.price else 0,
                "sale_count": p.sale_count or 0,
                "image_url": p.default_pic or "",
                "default_pic": p.default_pic or "",
                "brand_name": getattr(p, "brand_name", "") or "",
                "category_id": str(p.category_id) if p.category_id else "",
                "stock": getattr(p, "stock", 100) or 100,
                "score": 0.0,
                "_source": "db_filter",
            }
            for p in products
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "intent": None,
            "method": "db_filter",
        }

    # ── 排序 ──

    @staticmethod
    def _apply_sort(items: list[dict], sort_by: str) -> list[dict]:
        if sort_by == "price_asc":
            return sorted(items, key=lambda x: x.get("price", 0))
        elif sort_by == "price_desc":
            return sorted(items, key=lambda x: x.get("price", 0), reverse=True)
        elif sort_by == "sales":
            return sorted(items, key=lambda x: x.get("sale_count", 0), reverse=True)
        elif sort_by == "new":
            return sorted(items, key=lambda x: x.get("publish_time", ""), reverse=True)
        else:
            # default: 按融合分数降序
            return sorted(items, key=lambda x: x.get("score", 0), reverse=True)

    async def _db_ilike_fallback(
        self,
        keyword: str,
        category_id: str | None = None,
        brand_id: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort_by: str = "default",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """DB ILIKE 终极兜底 —— ES + vector 都不可用时。"""
        base = (
            select(PmsProduct)
            .where(PmsProduct.publish_status == 1)
            .where(PmsProduct.verify_status == 1)
            .where(PmsProduct.is_deleted.is_(False))
        )
        count_q = (
            select(func.count(PmsProduct.id))
            .where(PmsProduct.publish_status == 1)
            .where(PmsProduct.verify_status == 1)
            .where(PmsProduct.is_deleted.is_(False))
        )

        if keyword:
            keyword_pattern = f"%{keyword}%"
            keyword_filter = or_(
                PmsProduct.name.ilike(keyword_pattern),
                PmsProduct.sub_title.ilike(keyword_pattern),
                PmsProduct.keywords.ilike(keyword_pattern),
                PmsProduct.product_sn.ilike(keyword_pattern),
            )
            base = base.where(keyword_filter)
            count_q = count_q.where(keyword_filter)
        if category_id:
            base = base.where(PmsProduct.category_id == category_id)
            count_q = count_q.where(PmsProduct.category_id == category_id)
        if brand_id:
            base = base.where(PmsProduct.brand_id == brand_id)
            count_q = count_q.where(PmsProduct.brand_id == brand_id)
        if min_price is not None:
            base = base.where(PmsProduct.price >= min_price)
            count_q = count_q.where(PmsProduct.price >= min_price)
        if max_price is not None:
            base = base.where(PmsProduct.price <= max_price)
            count_q = count_q.where(PmsProduct.price <= max_price)

        sort_map = {
            "price_asc": PmsProduct.price.asc(),
            "price_desc": PmsProduct.price.desc(),
            "sales": PmsProduct.sale_count.desc(),
            "new": PmsProduct.created_at.desc(),
        }
        order_by = sort_map.get(sort_by, PmsProduct.sale_count.desc())

        result = await self._db.execute(count_q)
        total = result.scalar() or 0

        result = await self._db.execute(base.order_by(order_by).offset((page - 1) * page_size).limit(page_size))
        products = result.scalars().all()

        items = [
            {
                "id": str(p.id),
                "product_id": str(p.id),
                "name": p.name or "",
                "sub_title": p.sub_title or "",
                "price": float(p.price) if p.price else 0,
                "original_price": float(p.original_price) if p.original_price else None,
                "sale_count": p.sale_count or 0,
                "image_url": p.default_pic or "",
                "default_pic": p.default_pic or "",
                "brand_name": getattr(p, "brand_name", "") or "",
                "category_id": str(p.category_id) if p.category_id else "",
                "stock": getattr(p, "stock", 100) or 100,
                "score": 0.0,
                "_source": "db_ilike",
            }
            for p in products
        ]
        return items, total

    @staticmethod
    def _to_float(v: Any) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0


# ── Local embedding model cache ──

_local_embedding_model = None
_LOCAL_MODEL_NAME = "all-MiniLM-L6-v2"


def _safe_float(v: Any) -> float | None:
    """Convert to float, returning None on failure (unlike _to_float which returns 0)."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _get_local_embedding_model():
    """懒加载 sentence-transformers 模型 (线程安全, 单例)。"""
    global _local_embedding_model
    if _local_embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _local_embedding_model = SentenceTransformer(_LOCAL_MODEL_NAME, local_files_only=True)
    return _local_embedding_model
