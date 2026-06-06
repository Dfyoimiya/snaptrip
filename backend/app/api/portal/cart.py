"""
【前台商城 - 购物车 API】— /api/v1/portal/cart

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

from app.schemas.order import CartItemCreate, CartItemUpdate
from app.services.cart_service import CartService
from marketplace.app.models.users import User

router = APIRouter(prefix="/portal/cart", tags=["Portal - 购物车"])


@router.get("", summary="我的购物车")
async def list_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    items = await svc.list_items(current_user.id)
    return success([item.model_dump() for item in items])


@router.post("", summary="加入购物车", status_code=201)
async def add_item(
    data: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    result = await svc.add(current_user.id, data)
    return success(result.model_dump())


@router.put("/{item_id}", summary="修改购物车条目")
async def update_item(
    item_id: UUID,
    data: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    result = await svc.update_item(current_user.id, item_id, data)
    return success(result.model_dump())


@router.delete("/{item_id}", summary="删除购物车条目")
async def delete_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    await svc.delete_item(current_user.id, item_id)
    return success(message="删除成功")


@router.delete("", summary="清空购物车")
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    await svc.clear_cart(current_user.id)
    return success(message="购物车已清空")


@router.patch("/{item_id}/checked", summary="勾选/取消勾选")
async def toggle_checked(
    item_id: UUID,
    checked: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    result = await svc.update_item(current_user.id, item_id, CartItemUpdate(checked=checked))
    return success(result.model_dump())
