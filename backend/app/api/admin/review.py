"""后台管理 - 商品评价审核 API — /api/v1/admin/reviews

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_admin_user
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.review import ReviewListQuery, ReviewReplyCreate, ReviewResponse
from app.services.review_service import ReviewService

router = APIRouter(prefix="/admin/reviews", tags=["Admin - 评价管理"])


@router.get("", summary="评价列表 (管理端)")
async def list_reviews(
    product_id: UUID | None = Query(None, description="按商品筛选"),
    rating: int | None = Query(None, ge=1, le=5, description="按评分筛选"),
    status: int | None = Query(None, description="审核状态: 0=待审核 1=通过 2=驳回"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    query = ReviewListQuery(
        page=page,
        page_size=page_size,
        product_id=product_id,
        rating=rating,
        status=status,
    )
    svc = ReviewService(db)
    items, total = await svc.list_reviews(query)
    resp = PaginatedResponse.of(
        items=[ReviewResponse.model_validate(r).model_dump() for r in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.put("/{review_id}/approve", summary="审核通过")
async def approve_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = ReviewService(db)
    result = await svc.approve(review_id)
    if result is None:
        return success(None, message="评价不存在")
    return success(message="审核通过")


@router.put("/{review_id}/reject", summary="驳回评价")
async def reject_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = ReviewService(db)
    result = await svc.reject(review_id)
    if result is None:
        return success(None, message="评价不存在")
    return success(message="已驳回")


@router.post("/{review_id}/reply", summary="商家回复")
async def reply_review(
    review_id: UUID,
    data: ReviewReplyCreate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = ReviewService(db)
    result = await svc.reply(review_id, data.reply)
    if result is None:
        return success(None, message="评价不存在")
    return success(message="回复成功")
