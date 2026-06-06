"""
【后台管理 - 优惠券管理 API】— /api/v1/admin/coupons

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from marketplace.app.core.security import get_current_user
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.promotion import CouponCreate, CouponUpdate
from app.services.coupon_service import CouponService

router = APIRouter(prefix="/admin/coupons", tags=["Admin - 优惠券"])


@router.post("", summary="创建优惠券", status_code=201)
async def create(data: CouponCreate, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CouponService(db)
    result = await svc.create(data)
    return success(result.model_dump())


@router.put("/{coupon_id}", summary="编辑优惠券")
async def update(coupon_id: UUID, data: CouponUpdate, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CouponService(db)
    result = await svc.update(coupon_id, data)
    return success(result.model_dump())


@router.delete("/{coupon_id}", summary="删除优惠券")
async def delete(coupon_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CouponService(db)
    await svc.delete(coupon_id)
    return success(message="删除成功")


@router.get("/{coupon_id}", summary="优惠券详情")
async def get_detail(coupon_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CouponService(db)
    result = await svc.get_by_id(coupon_id)
    return success(result.model_dump())


@router.get("", summary="优惠券分页列表")
async def list_coupons(
    keyword: str | None = Query(None),
    type: int | None = Query(None, ge=0, le=2),
    status: int | None = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = CouponService(db)
    items, total = await svc.list_admin(keyword=keyword, type=type, status=status, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items], total=total, params=PaginationParams(page=page, page_size=page_size)
    )
    return success(resp.model_dump())


@router.get("/{coupon_id}/histories", summary="优惠券领取/使用记录")
async def get_histories(
    coupon_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), _u=Depends(get_current_user),
):
    svc = CouponService(db)
    items, total = await svc.get_histories(coupon_id, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items], total=total, params=PaginationParams(page=page, page_size=page_size)
    )
    return success(resp.model_dump())
