"""
【后台管理 - Banner/Subject/Help/Stats API】

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.cms import (
    BannerCreate,
    BannerUpdate,
    HelpCreate,
    HelpUpdate,
    SubjectCreate,
    SubjectUpdate,
)
from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.cms_service import CmsService, StatsService
from marketplace.app.core.security import get_current_user

# ── CMS Router ──

cms_router = APIRouter(prefix="/admin/cms", tags=["Admin - 内容管理"])


# --- Banners ---

@cms_router.get("/banners", summary="轮播图列表")
async def list_banners(status: int | None = Query(None, ge=0, le=1),
                       db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    items = await svc.list_banners(status=status)
    return success([i.model_dump() for i in items])


@cms_router.post("/banners", summary="新增轮播图", status_code=201)
async def create_banner(data: BannerCreate, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    result = await svc.create_banner(data)
    return success(result.model_dump())


@cms_router.put("/banners/{banner_id}", summary="编辑轮播图")
async def update_banner(banner_id: UUID, data: BannerUpdate,
                        db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    result = await svc.update_banner(banner_id, data)
    return success(result.model_dump())


@cms_router.delete("/banners/{banner_id}", summary="删除轮播图")
async def delete_banner(banner_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    await svc.delete_banner(banner_id)
    return success(message="删除成功")


@cms_router.patch("/banners/{banner_id}/sort", summary="修改排序")
async def sort_banner(banner_id: UUID, sort: int = Query(..., ge=0),
                      db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    result = await svc.toggle_banner(banner_id, "sort", sort)
    return success(result.model_dump())


@cms_router.patch("/banners/{banner_id}/status", summary="启用/禁用")
async def toggle_banner(banner_id: UUID, status: int = Query(..., ge=0, le=1),
                        db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    result = await svc.toggle_banner(banner_id, "status", status)
    return success(result.model_dump())


# --- Subjects ---

@cms_router.get("/subjects", summary="专题列表")
async def list_subjects(status: int | None = Query(None, ge=0, le=1),
                        page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                        db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    items, total = await svc.list_subjects(status=status, page=page, page_size=page_size)
    resp = PaginatedResponse.of(items=[i.model_dump() for i in items], total=total,
                                params=PaginationParams(page=page, page_size=page_size))
    return success(resp.model_dump())


@cms_router.get("/subjects/categories", summary="专题分类列表")
async def list_subject_categories(
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = CmsService(db)
    categories = await svc.list_subject_categories()
    return success(categories)


@cms_router.post("/subjects", summary="创建专题", status_code=201)
async def create_subject(data: SubjectCreate, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    result = await svc.create_subject(data)
    return success(result.model_dump())


@cms_router.put("/subjects/{subject_id}", summary="编辑专题")
async def update_subject(subject_id: UUID, data: SubjectUpdate,
                         db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    result = await svc.update_subject(subject_id, data)
    return success(result.model_dump())


@cms_router.delete("/subjects/{subject_id}", summary="删除专题")
async def delete_subject(subject_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    await svc.delete_subject(subject_id)
    return success(message="删除成功")


# --- Helps ---

@cms_router.get("/helps", summary="帮助列表")
async def list_helps(category_name: str | None = Query(None), status: int | None = Query(None, ge=0, le=1),
                     page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    items, total = await svc.list_helps(category_name=category_name, status=status, page=page, page_size=page_size)
    resp = PaginatedResponse.of(items=[i.model_dump() for i in items], total=total,
                                params=PaginationParams(page=page, page_size=page_size))
    return success(resp.model_dump())


@cms_router.post("/helps", summary="创建帮助", status_code=201)
async def create_help(data: HelpCreate, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    result = await svc.create_help(data)
    return success(result.model_dump())


@cms_router.put("/helps/{help_id}", summary="编辑帮助")
async def update_help(help_id: UUID, data: HelpUpdate,
                      db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    result = await svc.update_help(help_id, data)
    return success(result.model_dump())


@cms_router.delete("/helps/{help_id}", summary="删除帮助")
async def delete_help(help_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = CmsService(db)
    await svc.delete_help(help_id)
    return success(message="删除成功")


# ── Stats Router ──

stats_router = APIRouter(prefix="/admin/stats", tags=["Admin - 统计报表"])


@stats_router.get("/overview", summary="仪表盘概览")
async def dashboard_overview(db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = StatsService(db)
    result = await svc.get_dashboard_overview()
    return success(result.model_dump())


@stats_router.get("/sales", summary="销售趋势")
async def sales_stats(days: int = Query(7, ge=1, le=365),
                      db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = StatsService(db)
    items = await svc.get_sales_stats(days=days)
    return success([i.model_dump() for i in items])


@stats_router.get("/products", summary="商品销量排行")
async def product_rank(limit: int = Query(10, ge=1, le=100),
                       db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = StatsService(db)
    items = await svc.get_product_rank(limit=limit)
    return success([i.model_dump() for i in items])
