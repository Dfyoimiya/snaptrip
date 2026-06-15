"""
【前台商城 - 公告/帮助 API】— /api/v1/portal/notices

Author: SnapTrip Team
Date: 2026-06-14
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.cms_service import CmsService

router = APIRouter(prefix="/portal/notices", tags=["Portal - 公告/帮助"])


@router.get("", summary="公告/帮助列表")
async def list_notices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """前台公告列表 —— 只返回已启用的"""
    svc = CmsService(db)
    items, total = await svc.list_helps(status=1, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[item.model_dump() for item in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{notice_id}", summary="公告/帮助详情")
async def get_notice_detail(
    notice_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """单条公告详情 —— 通过 CmsHelp 实体"""
    from app.models.cms.content import CmsHelp
    from app.core.exceptions import ProductNotFoundError

    help_item = await db.get(CmsHelp, notice_id)
    if not help_item:
        raise ProductNotFoundError(str(notice_id))
    return success({
        "id": str(help_item.id),
        "title": help_item.title,
        "content": help_item.content,
        "category_name": help_item.category_name or "",
        "status": help_item.status,
        "sort": help_item.sort,
        "created_at": str(help_item.created_at) if help_item.created_at else "",
    })
