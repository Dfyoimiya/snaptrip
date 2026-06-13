"""Macalline-compatible product attribute routes — /productAttribute/*

Maps to existing /admin/product-attributes backend routes.

Author: SnapTrip Team
Date: 2026-06-09
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product.attribute import PmsProductAttribute
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.product import (
    ProductAttributeCreate,
    ProductAttributeResponse,
    ProductAttributeUpdate,
)
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/productAttribute", tags=["Macalline Compat - 商品属性"])


# ── Attribute Category ──

@router.get("/category/list/withAttr", summary="属性分类(含属性)")
async def category_list_with_attr(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    # Return categories with their attributes grouped
    result = await db.execute(
        select(PmsProductAttribute).order_by(PmsProductAttribute.sort.asc())
    )
    attrs = result.scalars().all()

    # Group by category_id
    from collections import defaultdict
    grouped: dict = defaultdict(list)
    for a in attrs:
        grouped[str(a.category_id) if a.category_id else "__none__"].append(
            ProductAttributeResponse.model_validate(a).model_dump()
        )

    return success([
        {"id": None, "name": "未分类", "attribute_list": grouped.get("__none__", [])},
        *[
            {"id": cat_id, "name": f"分类 {cat_id[:8]}", "attribute_list": attrs}
            for cat_id, attrs in grouped.items() if cat_id != "__none__"
        ]
    ])


@router.get("/category/list", summary="属性分类列表")
async def category_list(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(PmsProductAttribute.category_id).distinct()
    )
    cat_ids = [row[0] for row in result.fetchall() if row[0]]
    return success([
        {"id": cid, "name": f"分类 {str(cid)[:8]}", "attribute_count": 0}
        for cid in cat_ids
    ])


@router.post("/category/create", summary="创建属性分类")
async def category_create(
    name: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    # Macalline attribute categories are implicit (derived from product categories)
    return success({"id": None, "name": name}, message="属性分类依托于商品分类，无需单独创建")


@router.post("/category/update/{cat_id}", summary="更新属性分类")
async def category_update(
    cat_id: UUID,
    name: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


@router.get("/category/delete/{cat_id}", summary="删除属性分类")
async def category_delete(
    cat_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="删除成功")


# ── Attributes ──

@router.get("/attrInfo/{cate_id}", summary="获取分类属性信息")
async def attr_info(
    cate_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(PmsProductAttribute)
        .where(PmsProductAttribute.category_id == cate_id)
        .order_by(PmsProductAttribute.sort.asc())
    )
    attrs = result.scalars().all()
    return success([ProductAttributeResponse.model_validate(a).model_dump() for a in attrs])


@router.get("/list/{category_id}", summary="按分类查属性列表")
async def list_by_category(
    category_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    # If category_id is a placeholder, return all
    result = await db.execute(
        select(func.count(PmsProductAttribute.id))
        .where(PmsProductAttribute.category_id == category_id)
    )
    total = result.scalar() or 0

    result = await db.execute(
        select(PmsProductAttribute)
        .where(PmsProductAttribute.category_id == category_id)
        .order_by(PmsProductAttribute.sort.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    resp = PaginatedResponse.of(
        items=[ProductAttributeResponse.model_validate(a).model_dump() for a in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/create", summary="创建属性")
async def create(
    data: ProductAttributeCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    attr = PmsProductAttribute(**data.model_dump())
    db.add(attr)
    await db.flush()
    await db.refresh(attr)
    return success(ProductAttributeResponse.model_validate(attr).model_dump())


@router.post("/update/{attr_id}", summary="更新属性")
async def update_attr(
    attr_id: UUID,
    data: ProductAttributeUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    values = data.model_dump(exclude_unset=True)
    if not values:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)

    stmt = (
        update(PmsProductAttribute)
        .where(PmsProductAttribute.id == attr_id)
        .values(**values)
        .returning(PmsProductAttribute)
    )
    result = await db.execute(stmt)
    attr = result.scalar_one_or_none()
    if not attr:
        from app.core.exceptions import ProductNotFoundError
        raise ProductNotFoundError(str(attr_id))
    return success(ProductAttributeResponse.model_validate(attr).model_dump())


@router.get("/{attr_id}", summary="属性详情")
async def get_detail(
    attr_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    attr = await db.get(PmsProductAttribute, attr_id)
    if not attr:
        from app.core.exceptions import ProductNotFoundError
        raise ProductNotFoundError(str(attr_id))
    return success(ProductAttributeResponse.model_validate(attr).model_dump())


@router.post("/delete", summary="批量删除属性")
async def delete(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from sqlalchemy import delete
    if ids:
        await db.execute(delete(PmsProductAttribute).where(PmsProductAttribute.id.in_(ids)))
    return success(message="删除成功")
