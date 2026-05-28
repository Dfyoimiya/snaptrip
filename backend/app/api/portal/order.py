"""
【前台商城 - 订单 API】— /api/v1/portal/orders

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.core.security import get_current_user
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.order import OrderCreateFromCart
from app.services.order_service import OrderService
from marketplace.app.models.users import User

router = APIRouter(prefix="/portal/orders", tags=["Portal - 订单"])


@router.post("", summary="提交订单", status_code=201)
async def create_order(
    data: OrderCreateFromCart,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从购物车勾选项创建订单 —— 库存扣减 + 购物车清理均在同一事务中"""
    svc = OrderService(db)
    result = await svc.create_from_cart(current_user.id, current_user.email, data)
    return success(result.model_dump())


@router.get("", summary="我的订单列表")
async def list_my_orders(
    status: int | None = Query(None, ge=0, le=7),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrderService(db)
    items, total = await svc.list_user(current_user.id, status=status, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{order_id}", summary="订单详情")
async def get_detail(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrderService(db)
    result = await svc.get_detail(order_id)
    return success(result.model_dump())


@router.post("/{order_id}/cancel", summary="取消订单")
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrderService(db)
    result = await svc.cancel(order_id, operator=current_user.email, note="用户取消")
    return success(result.model_dump())


@router.post("/{order_id}/pay", summary="发起支付")
async def pay_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mock 支付 —— 直接标记已付款。生产环境需对接支付网关"""
    svc = OrderService(db)
    result = await svc.pay(order_id)
    return success(result.model_dump())


@router.post("/{order_id}/confirm-receipt", summary="确认收货")
async def confirm_receipt(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrderService(db)
    result = await svc.confirm_receipt(order_id)
    return success(result.model_dump())
