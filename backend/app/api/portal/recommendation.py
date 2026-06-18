"""前台 - 个性化推荐 API — /api/v1/portal/recommendations

调用 RecommendationSupervisor 执行 4-Agent 推荐流水线:
  UserProfileAgent → ProductRecAgent (recall → rerank) → InventoryAgent → MarketingCopyAgent

支持场景: homepage / product_detail / cart
支持可选认证: 登录用户返回个性化推荐, 匿名用户返回热门推荐

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from snaptrip_shared.core.response import success

from app.schemas.recommendation import RecommendationRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal/recommendations", tags=["Portal - 个性化推荐"])


def _get_supervisor(request: Request):
    """从 app state 获取 RecommendationSupervisor。"""
    svc = getattr(request.app.state, "recommendation_supervisor", None)
    if svc is None:
        raise RuntimeError("RecommendationSupervisor not initialized. Add in lifespan.")
    return svc


def _resolve_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> UUID | None:
    """从 Authorization header 解析 user_id (可选认证)。"""
    if not authorization:
        return None
    try:
        from marketplace.app.core.security import decode_access_token

        token = authorization.removeprefix("Bearer ").strip()
        payload = decode_access_token(token)
        sub = payload.get("sub", "")
        return UUID(sub) if sub else None
    except Exception:
        return None


@router.post("", summary="获取个性化推荐")
async def get_recommendations(
    body: RecommendationRequest,
    request: Request,
    user_id: UUID | None = Depends(_resolve_user_id),
):
    """个性化推荐核心端点。

    调用 4-Agent 推荐流水线, 返回个性化商品列表 + 文案。
    匿名用户返回热门推荐 (冷启动, 无用户画像)。
    """
    supervisor = _get_supervisor(request)

    # 合并 user_id (优先从 token 解析)
    if user_id and not body.user_id:
        body.user_id = str(user_id)

    response = await supervisor.recommend(body)

    return success(response.model_dump(mode="json"))


@router.get("/home", summary="首页快捷推荐")
async def get_home_recommendations(
    request: Request,
    user_id: UUID | None = Depends(_resolve_user_id),
    limit: int = Query(10, ge=1, le=30),
):
    """首页推荐快捷端点 (GET, 简单参数)。"""
    supervisor = _get_supervisor(request)

    req = RecommendationRequest(
        user_id=str(user_id) if user_id else None,
        scene="homepage",
        num_items=limit,
    )
    response = await supervisor.recommend(req)

    return success(response.model_dump(mode="json"))
