"""
【后台管理 - 会员管理 API】— /api/v1/admin/members

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
from app.services.member_service import MemberService
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/admin/members", tags=["Admin - 会员管理"])


@router.get("", summary="会员分页列表")
async def list_members(
    keyword: str | None = Query(None, description="邮箱搜索"),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = MemberService(db)
    items, total = await svc.list_admin(keyword=keyword, is_active=is_active, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items], total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{member_id}", summary="会员详情")
async def get_detail(member_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = MemberService(db)
    result = await svc.get_member_detail(member_id)
    return success(result)


@router.patch("/{member_id}/status", summary="启用/封禁会员")
async def toggle_status(
    member_id: UUID,
    is_active: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = MemberService(db)
    result = await svc.toggle_member_status(member_id, is_active)
    return success(result)
