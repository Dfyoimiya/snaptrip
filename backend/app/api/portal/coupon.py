"""
【前台商城 - 优惠券 API】— /api/v1/portal/coupons

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.coupon_service import CouponService
from marketplace.app.core.security import get_current_user
from marketplace.app.models.users import User

router = APIRouter(prefix="/portal/coupons", tags=["Portal - 优惠券"])


@router.get("/available", summary="可领取优惠券列表")
async def list_available(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    svc = CouponService(db)
    items, total = await svc.list_available(page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items], total=total, params=PaginationParams(page=page, page_size=page_size)
    )
    return success(resp.model_dump())


@router.post("/{coupon_id}/claim", summary="领取优惠券")
async def claim(
    coupon_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CouponService(db)
    result = await svc.claim(current_user.id, coupon_id)
    return success(result.model_dump())


@router.get("/mine", summary="我的优惠券")
async def my_coupons(
    use_status: int | None = Query(None, ge=0, le=2, description="0=未使用 1=已使用 2=已过期"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CouponService(db)
    items = await svc.list_my_coupons(current_user.id, use_status=use_status)
    return success([i.model_dump() for i in items])
