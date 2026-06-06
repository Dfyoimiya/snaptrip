"""
【后台管理 - 商品品牌 API】— /api/v1/admin/brands

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
from app.schemas.product import BrandCreate, BrandUpdate
from app.services.brand_service import BrandService

router = APIRouter(prefix="/admin/brands", tags=["Admin - 商品品牌"])


@router.post("", summary="创建品牌")
async def create(
    data: BrandCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = BrandService(db)
    result = await svc.create(data)
    return success(result.model_dump())


@router.put("/{brand_id}", summary="编辑品牌")
async def update(
    brand_id: UUID,
    data: BrandUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = BrandService(db)
    result = await svc.update(brand_id, data)
    return success(result.model_dump())


@router.delete("/{brand_id}", summary="删除品牌")
async def delete(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = BrandService(db)
    await svc.delete(brand_id)
    return success(message="删除成功")


@router.get("/all", summary="全部启用品牌")
async def list_all(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """无分页全返回 —— 用于商品编辑页下拉选择品牌"""
    svc = BrandService(db)
    items = await svc.list_all()
    return success([item.model_dump() for item in items])


@router.get("/{brand_id}", summary="品牌详情")
async def get_detail(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = BrandService(db)
    result = await svc.get_by_id(brand_id)
    return success(result.model_dump())


@router.get("", summary="品牌分页列表")
async def list_paginated(
    keyword: str | None = Query(None, description="搜索关键词"),
    first_letter: str | None = Query(None, description="首字母筛选"),
    factory_status: int | None = Query(None, description="制造商状态"),
    show_status: int | None = Query(None, description="显示状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = BrandService(db)
    items, total = await svc.list_paginated(
        keyword=keyword,
        first_letter=first_letter,
        factory_status=factory_status,
        show_status=show_status,
        page=page,
        page_size=page_size,
    )
    resp = PaginatedResponse.of(
        items=[item.model_dump() for item in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.patch("/{brand_id}/status", summary="切换品牌状态")
async def toggle_status(
    brand_id: UUID,
    field: str = Query(..., description="状态字段: show_status 或 factory_status"),
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = BrandService(db)
    result = await svc.toggle_status(brand_id, field, status)
    return success(result.model_dump())
