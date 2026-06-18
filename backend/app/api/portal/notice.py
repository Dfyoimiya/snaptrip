"""
【前台商城 - 公告/通知 API】— /api/v1/portal/notices

Author: SnapTrip Team
Date: 2026-06-18
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.cms_service import NoticeService

router = APIRouter(prefix="/portal/notices", tags=["Portal - 公告/通知"])


@router.get("", summary="公告/通知列表")
async def list_notices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """前台公告列表 —— 只返回已发布且目标类型为 ALL 或 CUSTOMER 的公告，按发布时间倒序。"""
    svc = NoticeService(db)
    items, total = await svc.list_portal_notices(page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[item.model_dump() for item in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{notice_id}", summary="公告/通知详情")
async def get_notice_detail(
    notice_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """单条公告详情 —— 通过 CmsNotice 实体。只返回已发布的。"""
    from app.core.exceptions import ProductNotFoundError
    from app.models.cms.notice import CmsNotice

    notice = await db.get(CmsNotice, notice_id)
    if not notice or notice.status != 1:
        raise ProductNotFoundError(str(notice_id))
    return success(
        {
            "id": str(notice.id),
            "title": notice.title,
            "content": notice.content or "",
            "target_type": notice.target_type,
            "status": notice.status,
            "publish_time": str(notice.publish_time) if notice.publish_time else "",
            "created_at": str(notice.created_at) if notice.created_at else "",
        }
    )
