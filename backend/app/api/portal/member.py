"""
【前台商城 - 会员中心 API】— /api/v1/portal/member

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
from app.schemas.member import AddressCreate, AddressUpdate
from app.services.member_service import MemberService
from marketplace.app.core.security import get_current_user
from marketplace.app.models.users import User

router = APIRouter(prefix="/portal/member", tags=["Portal - 会员中心"])


@router.get("/profile", summary="个人信息")
async def get_profile(db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    svc = MemberService(db)
    result = await svc.get_profile(u.id)
    return success(result.model_dump())


# ── 地址 ──

@router.get("/addresses", summary="收货地址列表")
async def list_addresses(db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    svc = MemberService(db)
    items = await svc.list_addresses(u.id)
    return success([i.model_dump() for i in items])


@router.post("/addresses", summary="新增地址", status_code=201)
async def create_address(data: AddressCreate, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    svc = MemberService(db)
    result = await svc.create_address(u.id, data)
    return success(result.model_dump())


@router.put("/addresses/{addr_id}", summary="编辑地址")
async def update_address(addr_id: UUID, data: AddressUpdate,
                         db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    svc = MemberService(db)
    result = await svc.update_address(u.id, addr_id, data)
    return success(result.model_dump())


@router.delete("/addresses/{addr_id}", summary="删除地址")
async def delete_address(addr_id: UUID, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    svc = MemberService(db)
    await svc.delete_address(u.id, addr_id)
    return success(message="删除成功")


# ── 收藏 ──

@router.get("/favorites", summary="我的收藏")
async def list_favorites(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                         db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    svc = MemberService(db)
    items, total = await svc.list_favorites(u.id, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items], total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/favorites", summary="添加收藏", status_code=201)
async def add_favorite(product_id: UUID = Query(...), db: AsyncSession = Depends(get_db),
                       u: User = Depends(get_current_user)):
    svc = MemberService(db)
    result = await svc.add_favorite(u.id, product_id)
    return success(result.model_dump())


@router.delete("/favorites/{product_id}", summary="取消收藏")
async def remove_favorite(product_id: UUID, db: AsyncSession = Depends(get_db),
                          u: User = Depends(get_current_user)):
    svc = MemberService(db)
    await svc.remove_favorite(u.id, product_id)
    return success(message="已取消收藏")
