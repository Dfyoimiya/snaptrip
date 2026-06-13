"""Resource & ResourceCategory management API.

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

from app.models.menu import Resource, ResourceCategory
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.rbac_admin import (
    ResourceCategoryCreate,
    ResourceCategoryResponse,
    ResourceCategoryUpdate,
    ResourceCreate,
    ResourceResponse,
    ResourceUpdate,
)
from marketplace.app.core.security import get_current_user

# Resource Category routes
rcat_router = APIRouter(prefix="/resourceCategory", tags=["System - 资源分类"])


@rcat_router.get("/listAll", summary="所有资源分类")
async def list_all_categories(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(ResourceCategory).order_by(ResourceCategory.sort.asc()))
    items = result.scalars().all()
    return success([ResourceCategoryResponse.model_validate(c).model_dump() for c in items])


@rcat_router.post("/create", summary="创建资源分类")
async def create_category(
    data: ResourceCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    cat = ResourceCategory(**data.model_dump())
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return success(ResourceCategoryResponse.model_validate(cat).model_dump())


@rcat_router.post("/update/{cat_id}", summary="更新资源分类")
async def update_category(
    cat_id: UUID,
    data: ResourceCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    cat = await db.get(ResourceCategory, cat_id)
    if not cat:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="NOT_FOUND", message="资源分类不存在", status_code=404)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    await db.flush()
    await db.refresh(cat)
    return success(ResourceCategoryResponse.model_validate(cat).model_dump())


@rcat_router.post("/delete/{cat_id}", summary="删除资源分类")
async def delete_category(
    cat_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    cat = await db.get(ResourceCategory, cat_id)
    if not cat:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="NOT_FOUND", message="资源分类不存在", status_code=404)
    await db.delete(cat)
    return success(message="删除成功")


# Resource routes
res_router = APIRouter(prefix="/resource", tags=["System - 资源"])


@res_router.get("/listAll", summary="所有资源")
async def list_all_resources(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(Resource).order_by(Resource.name.asc()))
    items = result.scalars().all()
    return success([ResourceResponse.model_validate(r).model_dump() for r in items])


@res_router.get("/list", summary="资源分页列表")
async def list_resources(
    category_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    base = select(Resource)
    count_q = select(func.count(Resource.id))
    if category_id:
        base = base.where(Resource.category_id == category_id)
        count_q = count_q.where(Resource.category_id == category_id)

    result = await db.execute(count_q)
    total = result.scalar() or 0

    result = await db.execute(
        base.order_by(Resource.name.asc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()

    resp = PaginatedResponse.of(
        items=[ResourceResponse.model_validate(r).model_dump() for r in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@res_router.post("/create", summary="创建资源")
async def create_resource(
    data: ResourceCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    res = Resource(**data.model_dump())
    db.add(res)
    await db.flush()
    await db.refresh(res)
    return success(ResourceResponse.model_validate(res).model_dump())


@res_router.post("/update/{res_id}", summary="更新资源")
async def update_resource(
    res_id: UUID,
    data: ResourceUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    res = await db.get(Resource, res_id)
    if not res:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="NOT_FOUND", message="资源不存在", status_code=404)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(res, k, v)
    await db.flush()
    await db.refresh(res)
    return success(ResourceResponse.model_validate(res).model_dump())


@res_router.post("/delete/{res_id}", summary="删除资源")
async def delete_resource(
    res_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    res = await db.get(Resource, res_id)
    if not res:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="NOT_FOUND", message="资源不存在", status_code=404)
    await db.delete(res)
    return success(message="删除成功")
