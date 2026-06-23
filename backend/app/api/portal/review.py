"""前台 - 商品评价 API — /api/v1/portal/reviews

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from snaptrip_shared.core.response import APIServiceError, success
from snaptrip_shared.db.session import get_db
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order.order import OmsOrder, OmsOrderItem
from app.models.product.review import PmsProductReview
from app.schemas.admin_notification import AdminNotificationCreate
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.review import (
    ReviewCreate,
    ReviewEligibilityResponse,
    ReviewListQuery,
    ReviewResponse,
    ReviewStatsResponse,
    ReviewUpdate,
)
from app.services.admin_notification_service import AdminNotificationService
from app.services.review_service import ReviewService
from marketplace.app.core.security import get_current_user, oauth2_scheme
from marketplace.app.models.users import User

router = APIRouter(prefix="/portal/reviews", tags=["Portal - 商品评价"])


# ── 可选认证依赖 ──


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """尝试获取当前用户; 未认证时返回 None 而非 401。"""
    if token is None:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except HTTPException:
        return None


# ── 评价 CRUD ──


@router.post("", summary="创建评价", status_code=201)
async def create_review(
    data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ReviewService(db)
    # 预检查：用户是否已评论过该商品
    existing = await svc.get_by_user_and_product(current_user.id, data.product_id)
    if existing:
        raise APIServiceError(code=40001, message="您已评价过该商品")
    result = await svc.create(current_user.id, data)
    content_preview = (data.content or "").strip()
    if len(content_preview) > 40:
        content_preview = f"{content_preview[:40]}…"
    await AdminNotificationService(db).notify_admins(
        AdminNotificationCreate(
            type="review_created",
            title="新评价待审核",
            body=f"{data.rating} 星评价：{content_preview or '用户未填写文字评价'}",
            action_url="/pms/product",
        )
    )
    return success(result.id, message="评价成功")


@router.get("", summary="评价列表")
async def list_reviews(
    product_id: UUID | None = Query(None, description="按商品筛选"),
    rating: int | None = Query(None, ge=1, le=5, description="按评分筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    query = ReviewListQuery(
        page=page,
        page_size=page_size,
        product_id=product_id,
        rating=rating,
        status=1,  # 公开列表只展示已通过审核的
    )
    svc = ReviewService(db)
    viewer_id = current_user.id if current_user else None
    items, total = await svc.list_reviews(query, viewer_user_id=viewer_id)
    resp = PaginatedResponse.of(
        items=[ReviewResponse.model_validate(r).model_dump() for r in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


# ── 评价资格校验 ──


@router.get("/check-eligibility", summary="检查评价资格")
async def check_review_eligibility(
    product_id: UUID = Query(..., description="商品ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """检查当前用户是否有资格评价该商品。

    规则:
      - 用户必须购买过该商品
      - 订单必须处于"已收货"状态 (status=3)
      - 用户尚未评价过该商品
    """
    # 1. 检查是否已评价
    existing_review_result = await db.execute(
        select(PmsProductReview.id).where(
            PmsProductReview.user_id == current_user.id,
            PmsProductReview.product_id == product_id,
            PmsProductReview.is_deleted == False,  # noqa: E712
        )
    )
    already_reviewed = existing_review_result.scalar_one_or_none() is not None

    # 2. 查询包含该商品的用户订单 (JOIN OmsOrder + OmsOrderItem)
    order_query_result = await db.execute(
        select(OmsOrder.id, OmsOrder.order_sn, OmsOrder.status)
        .join(OmsOrderItem, OmsOrder.id == OmsOrderItem.order_id)
        .where(
            OmsOrder.user_id == current_user.id,
            OmsOrder.delete_status == 0,
            OmsOrderItem.product_id == product_id,
        )
        .order_by(OmsOrder.created_at.desc())
    )
    orders = order_query_result.all()  # list[(UUID, str, int)]

    # 3. 判定资格
    if already_reviewed:
        resp = ReviewEligibilityResponse(
            eligible=False,
            reason="您已评价过该商品",
            already_reviewed=True,
        )
    elif not orders:
        resp = ReviewEligibilityResponse(
            eligible=False,
            reason="您尚未购买该商品",
            already_reviewed=False,
        )
    else:
        received_orders = [o for o in orders if o[2] == 3]
        if received_orders:
            resp = ReviewEligibilityResponse(
                eligible=True,
                order_id=str(received_orders[0][0]),  # order UUID
                already_reviewed=False,
            )
        else:
            resp = ReviewEligibilityResponse(
                eligible=False,
                reason="确认收货后才能评价",
                already_reviewed=False,
            )

    return success(resp.model_dump())


# ── 评价统计 ──


@router.get("/stats", summary="商品评价统计")
async def get_review_stats(
    product_id: UUID = Query(..., description="商品ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取商品评价聚合统计 (公开接口, 无需登录)。"""
    # 查询所有已审核通过的评价, 按评分分组统计
    stats_result = await db.execute(
        select(
            PmsProductReview.rating,
            func.count(PmsProductReview.id).label("count"),
        )
        .where(
            PmsProductReview.product_id == product_id,
            PmsProductReview.status == 1,
            PmsProductReview.is_deleted == False,  # noqa: E712
        )
        .group_by(PmsProductReview.rating)
    )
    rows = stats_result.all()  # list[(int, int)]

    # 构建分布 (确保 1~5 星都有默认值 0)
    distribution: dict[int, int] = {i: 0 for i in range(1, 6)}
    total_rating_sum = 0
    total_count = 0

    for row in rows:
        rating: int = row[0]
        count: int = row[1]
        distribution[rating] = count
        total_rating_sum += rating * count
        total_count += count

    average_rating = round(total_rating_sum / total_count, 1) if total_count > 0 else 0.0

    resp = ReviewStatsResponse(
        product_id=product_id,
        average_rating=average_rating,
        total_count=total_count,
        distribution=distribution,
    )
    return success(resp.model_dump())


@router.get("/{review_id}", summary="评价详情")
async def get_review(review_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = ReviewService(db)
    result = await svc.get_by_id(review_id)
    if result is None:
        return success(None, message="评价不存在")
    return success(ReviewResponse.model_validate(result).model_dump())


@router.put("/{review_id}", summary="修改评价")
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ReviewService(db)
    result = await svc.update(review_id, current_user.id, data)
    if result is None:
        return success(None, message="评价不存在或无权修改")
    return success(ReviewResponse.model_validate(result).model_dump(), message="修改成功, 待重新审核")


@router.delete("/{review_id}", summary="删除评价")
async def delete_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ReviewService(db)
    ok = await svc.delete(review_id, current_user.id)
    if not ok:
        return success(None, message="评价不存在或无权删除")
    return success(message="删除成功")
