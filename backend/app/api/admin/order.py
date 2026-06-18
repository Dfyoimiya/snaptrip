"""
【后台管理 - 订单管理 API】— /api/v1/admin/orders

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_admin_user
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.order import (
    OrderDeliveryRequest,
    OrderListQuery,
    OrderPriceModifyRequest,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/admin/orders", tags=["Admin - 订单管理"])


@router.get("", summary="订单分页列表")
async def list_orders(
    order_sn: str | None = Query(None),
    status: int | None = Query(None, ge=0, le=7),
    start_time: str | None = Query(None),
    end_time: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    from datetime import datetime as dt

    query = OrderListQuery(
        order_sn=order_sn,
        status=status,
        start_time=dt.fromisoformat(start_time) if start_time else None,
        end_time=dt.fromisoformat(end_time) if end_time else None,
        page=page,
        page_size=page_size,
    )
    svc = OrderService(db)
    items, total = await svc.list_admin(query)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{order_id}", summary="订单详情")
async def get_detail(order_id: UUID, db: AsyncSession = Depends(get_db), _current_user=Depends(require_admin_user)):
    svc = OrderService(db)
    result = await svc.get_detail(order_id)
    return success(result.model_dump())


@router.post("/{order_id}/close", summary="关闭订单")
async def close_order(
    order_id: UUID,
    note: str = Query("", description="关闭原因"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = OrderService(db)
    result = await svc.admin_close(order_id, note=note, operator=_current_user.email)
    return success(result.model_dump())


@router.post("/{order_id}/delivery", summary="订单发货")
async def delivery(
    order_id: UUID,
    data: OrderDeliveryRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = OrderService(db)
    result = await svc.delivery(order_id, data, operator=_current_user.email)
    return success(result.model_dump())


@router.post("/{order_id}/modify-address", summary="修改收货地址")
async def modify_address(
    order_id: UUID,
    receiver_name: str | None = Query(None),
    receiver_phone: str | None = Query(None),
    receiver_detail_address: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = OrderService(db)
    result = await svc.modify_address(
        order_id,
        receiver_name=receiver_name,
        receiver_phone=receiver_phone,
        receiver_detail_address=receiver_detail_address,
    )
    return success(result.model_dump())


@router.post("/{order_id}/modify-price", summary="修改订单金额")
async def modify_price(
    order_id: UUID,
    data: OrderPriceModifyRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = OrderService(db)
    result = await svc.modify_price(order_id, data)
    return success(result.model_dump())


@router.post("/{order_id}/remark", summary="添加管理员备注")
async def remark(
    order_id: UUID,
    note: str = Query(..., min_length=1, description="备注内容"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = OrderService(db)
    result = await svc.remark(order_id, note)
    return success(result.model_dump())


@router.post("/{order_id}/refund", summary="退款完成")
async def refund_order(
    order_id: UUID,
    note: str = Query("", description="退款备注"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """管理员确认退款 —— 从退款中过渡到已退款"""
    svc = OrderService(db)
    result = await svc.refund(order_id, operator=_current_user.email, note=note)
    return success(result.model_dump())


@router.delete("/{order_id}", summary="删除订单（软删除）")
async def delete_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = OrderService(db)
    await svc.admin_delete(order_id)
    return success(message="删除成功")
