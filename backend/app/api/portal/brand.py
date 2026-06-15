"""
【前台商城 - 品牌浏览 API】— /api/v1/portal/brands

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
from app.services.brand_service import BrandService

router = APIRouter(prefix="/portal/brands", tags=["Portal - 品牌"])


@router.get("", summary="品牌列表")
async def list_brands(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """前台品牌列表 —— 只返回显示状态的品牌"""
    svc = BrandService(db)
    items, total = await svc.list_paginated(show_status=1, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[item.model_dump() for item in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{brand_id}", summary="品牌详情")
async def get_brand_detail(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    svc = BrandService(db)
    result = await svc.get_by_id(brand_id)
    return success(result.model_dump())
