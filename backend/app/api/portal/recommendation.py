"""前台 - 个性化推荐 API — /api/v1/portal/recommendations

管道: QueryUnderstanding → UnifiedRecallService (5路) → FusionWeights → Diversity → Response

支持场景: homepage / product_detail / cart
支持可选认证: 登录用户使用 CF + vector 通道, 匿名用户使用 trending 通道

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import AsyncSessionLocal

from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal/recommendations", tags=["Portal - 个性化推荐"])


# ── Dependencies ─────────────────────────────────────────────────────────────


def _get_recall_service(request: Request):
    """Build UnifiedRecallService from available backend services."""
    from app.services.recall_service import UnifiedRecallService

    es_client = getattr(request.app.state, "es_client", None)
    if es_client is None:
        try:
            from app.search.client import get_search_client
            es_client = get_search_client()
        except Exception:
            pass

    return UnifiedRecallService(
        es_client=es_client,
        vector_service=getattr(request.app.state, "vector_search_service", None),
        cf_service=getattr(request.app.state, "cf_service", None),
        trending_service=getattr(request.app.state, "trending_service", None),
        db_factory=AsyncSessionLocal,
    )


def _get_query_understanding(request: Request):
    """Build QueryUnderstandingService (may be None if LLM unavailable)."""
    llm = getattr(request.app.state, "llm_adapter", None)
    if not llm:
        return None
    from app.services.query_understanding_service import QueryUnderstandingService

    return QueryUnderstandingService(llm_adapter=llm, memory=request.app.state.memory)


def _resolve_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> uuid.UUID | None:
    """从 Authorization header 解析 user_id (可选认证)。"""
    if not authorization:
        return None
    try:
        from marketplace.app.core.security import decode_access_token

        token = authorization.removeprefix("Bearer ").strip()
        payload = decode_access_token(token)
        sub = payload.get("sub", "")
        return uuid.UUID(sub) if sub else None
    except Exception:
        return None


# ── Shared recommendation logic ──────────────────────────────────────────────


async def _do_recommend(
    request: Request,
    *,
    uid: str | None,
    session_id: str | None = None,
    scene: str = "homepage",
    num_items: int = 10,
    query: str | None = None,
    product_id: str | None = None,
    user_segment: str | None = None,
) -> RecommendationResponse:
    """核心推荐管道, POST 和 GET 端点共用。

    1. QueryUnderstanding (有 query 时)
    2. UnifiedRecallService 5路并行召回
    3. FusionWeights 分群调整
    4. DiversityService 类目多样性重排
    5. RecommendationResponse
    """
    t_start = time.perf_counter()

    recall = _get_recall_service(request)
    qu = _get_query_understanding(request)

    # ── Step 1: Query Understanding ──
    intent = "navigational"
    weights = None
    rewritten_query = query
    pre_embedding: list[float] | None = None

    if qu and query:
        try:
            qu_result = await qu.understand(query, with_embedding=True, with_expansion=False)
            intent = qu_result.intent
            weights = dict(qu_result.weights)
            if qu_result.rewritten_query and qu_result.rewritten_query != query:
                rewritten_query = qu_result.rewritten_query
                logger.debug("recommend: query rewritten: %s → %s", query, rewritten_query)
            pre_embedding = qu_result.embedding
        except Exception as exc:
            logger.debug("recommend: query_understanding failed: %s", exc)

    # ── Step 2: Multi-channel recall ──
    channels = ["es", "vector", "cf", "trending"] if uid else ["trending", "attribute"]
    candidates = await recall.recall(
        query=rewritten_query,
        user_id=uid,
        embedding=pre_embedding,
        channels=channels,
        budget=num_items * 3,
    )

    # ── Step 3: Segment-aware fusion weight adjustment ──
    if user_segment and weights:
        try:
            from app.services.fusion_weight_service import apply_segment_weights
            weights = apply_segment_weights(weights, user_segment)
        except Exception as exc:
            logger.debug("recommend: fusion_weight adjustment failed: %s", exc)

    # ── Step 4: Diversity re-rank ──
    if len(candidates) > num_items:
        try:
            from app.services.diversity_service import DiversityService
            candidates = DiversityService.apply_category_spread(
                candidates,
                top_n=num_items,
                min_categories=3,
                max_per_category=2,
            )
        except Exception as exc:
            logger.debug("recommend: diversity failed: %s", exc)

    # ── Step 5: Format response ──
    products = [
        {
            "product_id": c["product_id"],
            "name": c["name"],
            "category_id": c.get("category_id", ""),
            "price": c.get("price", 0),
            "brand_name": c.get("brand_name", ""),
            "image_url": c.get("image_url", ""),
            "sale_count": c.get("sale_count", 0),
            "stock": c.get("stock", 0),
            "score": c["score"],
            "marketing_copy": "",
        }
        for c in candidates[:num_items]
    ]

    total_latency_ms = (time.perf_counter() - t_start) * 1000

    logger.info(
        "recommend: scene=%s uid=%s candidates=%d final=%d latency_ms=%.1f intent=%s",
        scene,
        uid,
        len(candidates),
        len(products),
        total_latency_ms,
        intent,
    )

    return RecommendationResponse(
        request_id=str(uuid.uuid4())[:8],
        user_id=uid,
        session_id=session_id,
        products=products,
        copies=[],
        experiment_group="control",
        agent_results={},
        total_latency_ms=total_latency_ms,
        timestamp=datetime.now(UTC),
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("", summary="获取个性化推荐")
async def get_recommendations(
    body: RecommendationRequest,
    request: Request,
    user_id: uuid.UUID | None = Depends(_resolve_user_id),
):
    """个性化推荐核心端点 (POST)。

    使用 UnifiedRecallService 多路召回 + QueryUnderstanding + Diversity:
      - 登录用户: ES + vector + CF + trending
      - 匿名用户: trending + attribute
      - 有 query: 查询改写 + 预计算向量
    """
    uid = str(user_id) if user_id else (body.user_id or None)

    query = (body.context or {}).get("query") or (body.context or {}).get("keyword") or None

    response = await _do_recommend(
        request,
        uid=uid,
        session_id=body.session_id,
        scene=body.scene,
        num_items=body.num_items,
        query=query,
        product_id=body.product_id,
    )
    return success(response.model_dump())


@router.get("/home", summary="首页快捷推荐")
async def get_home_recommendations(
    request: Request,
    user_id: uuid.UUID | None = Depends(_resolve_user_id),
    limit: int = Query(10, ge=1, le=30),
):
    """首页推荐快捷端点 (GET)。

    参数极简, 适用于首页首屏快速加载。
    """
    uid = str(user_id) if user_id else None

    response = await _do_recommend(
        request,
        uid=uid,
        scene="homepage",
        num_items=limit,
    )
    return success(response.model_dump())
