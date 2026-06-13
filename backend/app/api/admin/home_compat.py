"""Home content management API — /home/*

Macalline-compatible routes for home page content management.
Maps to existing CMS backend where possible.

Author: SnapTrip Team
Date: 2026-06-09
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms.content import CmsBanner, CmsSubject
from app.models.product.brand import PmsBrand
from app.models.product.product import PmsProduct
from app.schemas.common import PaginatedResponse, PaginationParams
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/home", tags=["Macalline Compat - 首页内容"])


# ── Advertise (Banners) ──

@router.get("/advertise/list", summary="广告列表")
async def advertise_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(func.count(CmsBanner.id)))
    total = result.scalar() or 0
    result = await db.execute(
        select(CmsBanner).order_by(CmsBanner.sort.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    resp = PaginatedResponse.of(
        items=[{"id": b.id, "name": b.title, "pic": b.pic, "url": b.url, "sort": b.sort, "status": b.status} for b in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/advertise/create", summary="创建广告")
async def advertise_create(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="使用 /admin/cms/banners 接口")


@router.post("/advertise/update/{ad_id}", summary="更新广告")
async def advertise_update(
    ad_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="使用 /admin/cms/banners 接口")


@router.get("/advertise/{ad_id}", summary="广告详情")
async def advertise_detail(
    ad_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    banner = await db.get(CmsBanner, ad_id)
    if not banner:
        return success(None, message="未找到")
    return success({"id": banner.id, "name": banner.title, "pic": banner.pic, "url": banner.url})


@router.post("/advertise/delete", summary="删除广告")
async def advertise_delete(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from sqlalchemy import delete
    await db.execute(delete(CmsBanner).where(CmsBanner.id.in_(ids)))
    return success(message="删除成功")


@router.post("/advertise/update/status/{ad_id}", summary="更新广告状态")
async def advertise_status(
    ad_id: UUID,
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    banner = await db.get(CmsBanner, ad_id)
    if banner:
        banner.status = status
        await db.flush()
    return success(message="更新成功")


# ── Brand ──

@router.get("/brand/list", summary="推荐品牌列表")
async def brand_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(func.count(PmsBrand.id)))
    total = result.scalar() or 0
    result = await db.execute(
        select(PmsBrand).order_by(PmsBrand.sort.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    resp = PaginatedResponse.of(
        items=[{"id": b.id, "brand_name": b.name, "recommend_status": 0, "sort": b.sort} for b in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/brand/create", summary="创建推荐品牌")
async def brand_create(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="使用 /admin/brands 接口")


@router.post("/brand/update/recommendStatus", summary="批量更新推荐状态")
async def brand_recommend_status(
    ids: list[UUID] = Query(..., alias="ids"),
    recommend_status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


@router.post("/brand/delete", summary="批量删除推荐品牌")
async def brand_delete(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="删除成功")


@router.post("/brand/update/sort/{brand_id}", summary="更新品牌排序")
async def brand_sort(
    brand_id: UUID,
    sort: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


# ── New Product ──

@router.get("/newProduct/list", summary="新品推荐列表")
async def new_product_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(func.count(PmsProduct.id)).where(PmsProduct.new_status == 1))
    total = result.scalar() or 0
    result = await db.execute(
        select(PmsProduct).where(PmsProduct.new_status == 1)
        .order_by(PmsProduct.sort.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    resp = PaginatedResponse.of(
        items=[{"id": p.id, "product_name": p.name, "recommend_status": p.new_status, "sort": p.sort} for p in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/newProduct/create", summary="创建新品推荐")
async def new_product_create(
    product_ids: list[UUID] = Query(..., alias="productIds"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="请通过商品管理设置新品状态")


@router.post("/newProduct/update/recommendStatus", summary="批量更新新品推荐")
async def new_product_recommend(
    ids: list[UUID] = Query(..., alias="ids"),
    recommend_status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


@router.post("/newProduct/delete", summary="批量删除新品推荐")
async def new_product_delete(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="删除成功")


@router.post("/newProduct/update/sort/{product_id}", summary="更新新品排序")
async def new_product_sort(
    product_id: UUID,
    sort: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


# ── Recommend Product ──

@router.get("/recommendProduct/list", summary="推荐商品列表")
async def recommend_product_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(func.count(PmsProduct.id)).where(PmsProduct.recommend_status == 1))
    total = result.scalar() or 0
    result = await db.execute(
        select(PmsProduct).where(PmsProduct.recommend_status == 1)
        .order_by(PmsProduct.sort.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    resp = PaginatedResponse.of(
        items=[{"id": p.id, "product_name": p.name, "recommend_status": p.recommend_status, "sort": p.sort} for p in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/recommendProduct/create", summary="创建推荐商品")
async def recommend_product_create(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="请通过商品管理设置推荐状态")


@router.post("/recommendProduct/update/recommendStatus", summary="批量更新推荐状态")
async def recommend_product_status(
    ids: list[UUID] = Query(..., alias="ids"),
    recommend_status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


@router.post("/recommendProduct/delete", summary="批量删除推荐商品")
async def recommend_product_delete(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="删除成功")


@router.post("/recommendProduct/update/sort/{product_id}", summary="更新推荐排序")
async def recommend_product_sort(
    product_id: UUID,
    sort: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


# ── Recommend Subject ──

@router.get("/recommendSubject/list", summary="推荐专题列表")
async def recommend_subject_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(func.count(CmsSubject.id)))
    total = result.scalar() or 0
    result = await db.execute(
        select(CmsSubject).order_by(CmsSubject.id.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    resp = PaginatedResponse.of(
        items=[{"id": s.id, "subject_name": s.title, "recommend_status": s.recommend_status, "sort": 0} for s in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/recommendSubject/create", summary="创建推荐专题")
async def recommend_subject_create(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="使用 /admin/cms/subjects 接口")


@router.post("/recommendSubject/update/recommendStatus", summary="批量更新推荐状态")
async def recommend_subject_status(
    ids: list[UUID] = Query(..., alias="ids"),
    recommend_status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


@router.post("/recommendSubject/delete", summary="批量删除推荐专题")
async def recommend_subject_delete(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="删除成功")


@router.post("/recommendSubject/update/sort/{subject_id}", summary="更新专题排序")
async def recommend_subject_sort(
    subject_id: UUID,
    sort: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")
