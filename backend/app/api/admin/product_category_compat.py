"""Macalline-compatible product category routes — /productCategory/*

Maps to existing /admin/categories backend routes.

Author: SnapTrip Team
Date: 2026-06-09
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.product import CategoryCreate, CategoryUpdate
from app.services.category_service import CategoryService
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/productCategory", tags=["Macalline Compat - 商品分类"])


def _build_tree(nodes, parent_id=None):
    children = [n for n in nodes if (n.get("parent_id") if isinstance(n, dict) else n.parent_id) == parent_id]
    result = []
    for c in children:
        if isinstance(c, dict):
            c["children"] = _build_tree(nodes, c["id"])
            result.append(c)
        else:
            d = c.model_dump()
            d["children"] = _build_tree(nodes, d["id"])
            result.append(d)
    return result


@router.get("/list/withChildren", summary="分类列表(含子分类)")
async def list_with_children(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    tree = await svc.get_tree()
    data = [node.model_dump() for node in tree]
    return success(data)


@router.get("/list/{parent_id}", summary="按父级查子分类")
async def list_by_parent(
    parent_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    items, total = await svc.list_paginated(parent_id=parent_id, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[item.model_dump() for item in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/create", summary="创建分类")
async def create(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    result = await svc.create(data)
    return success(result.model_dump())


@router.post("/update/{category_id}", summary="更新分类")
async def update(
    category_id: UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    result = await svc.update(category_id, data)
    return success(result.model_dump())


@router.get("/{category_id}", summary="分类详情")
async def get_detail(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    result = await svc.get_by_id(category_id)
    return success(result.model_dump())


@router.post("/delete/{category_id}", summary="删除分类")
async def delete(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    await svc.delete(category_id)
    return success(message="删除成功")


@router.post("/update/navStatus", summary="更新导航状态")
async def update_nav_status(
    ids: list[UUID] = Query(..., alias="ids"),
    nav_status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    for cid in ids:
        await svc.toggle_status(cid, "nav_status", nav_status)
    return success(message="更新成功")


@router.post("/update/showStatus", summary="更新显示状态")
async def update_show_status(
    ids: list[UUID] = Query(..., alias="ids"),
    show_status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    for cid in ids:
        await svc.toggle_status(cid, "show_status", show_status)
    return success(message="更新成功")
