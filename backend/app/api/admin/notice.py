"""
【后台管理 - 公告管理 API】— /api/v1/admin/notices

Author: SnapTrip Team
Date: 2026-06-18
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_admin_user
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.notice import NoticeCreate, NoticeUpdate
from app.services.cms_service import NoticeService

router = APIRouter(prefix="/admin/notices", tags=["Admin - 公告管理"])


@router.post("", summary="创建公告", status_code=201)
async def create_notice(
    data: NoticeCreate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = NoticeService(db)
    result = await svc.create_notice(data)
    return success(result.model_dump())


@router.put("/{notice_id}", summary="编辑公告")
async def update_notice(
    notice_id: UUID,
    data: NoticeUpdate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = NoticeService(db)
    result = await svc.update_notice(notice_id, data)
    return success(result.model_dump())


@router.delete("/{notice_id}", summary="删除公告")
async def delete_notice(
    notice_id: UUID,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = NoticeService(db)
    await svc.delete_notice(notice_id)
    return success(message="删除成功")


@router.get("", summary="公告列表（分页）")
async def list_notices(
    target_type: str | None = Query(None, description="筛选目标类型: ALL/CUSTOMER/MERCHANT"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = NoticeService(db)
    items, total = await svc.list_notices(target_type=target_type, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{notice_id}", summary="公告详情")
async def get_notice(
    notice_id: UUID,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = NoticeService(db)
    result = await svc.get_notice(notice_id)
    return success(result.model_dump())


@router.patch("/{notice_id}/status", summary="发布/隐藏公告")
async def toggle_notice_status(
    notice_id: UUID,
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    svc = NoticeService(db)
    result = await svc.toggle_notice_status(notice_id, status)
    return success(result.model_dump())
