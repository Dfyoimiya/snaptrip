"""
【后台管理 - 商品属性 API】— /api/v1/admin/product-attributes

管理员为每个分类定义属性模板（如分类"手机"下定义属性"屏幕尺寸"），
编辑商品时按模板填写属性值。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product.attribute import PmsProductAttribute
from app.models.product.category import PmsCategory
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.product import (
    ProductAttributeCreate,
    ProductAttributeResponse,
    ProductAttributeUpdate,
)
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/admin/product-attributes", tags=["Admin - 商品属性"])


@router.post("", summary="创建属性")
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


@router.put("/{attr_id}", summary="编辑属性")
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


@router.delete("/{attr_id}", summary="删除属性")
async def delete(
    attr_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    attr = await db.get(PmsProductAttribute, attr_id)
    if not attr:
        from app.core.exceptions import ProductNotFoundError
        raise ProductNotFoundError(str(attr_id))
    await db.delete(attr)
    return success(message="删除成功")


# ── Attribute Categories ──
# NOTE: MUST be registered before GET /{attr_id} to avoid "categories" matching as attr_id


@router.get("/categories", summary="属性分类列表(含属性)")
async def list_categories_with_attrs(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return product categories that have attributes, with nested attribute lists."""
    result = await db.execute(
        select(PmsProductAttribute).order_by(PmsProductAttribute.sort.asc())
    )
    attrs = result.scalars().all()

    grouped: dict = defaultdict(list)
    cat_ids_set: set = set()
    for a in attrs:
        key = str(a.category_id) if a.category_id else "__none__"
        grouped[key].append(ProductAttributeResponse.model_validate(a).model_dump())
        if a.category_id:
            cat_ids_set.add(a.category_id)

    cat_names: dict = {}
    if cat_ids_set:
        result = await db.execute(
            select(PmsCategory).where(PmsCategory.id.in_(cat_ids_set))
        )
        for cat in result.scalars().all():
            cat_names[str(cat.id)] = cat.name

    items: list[dict] = []
    if "__none__" in grouped:
        items.append({
            "id": None,
            "name": "未分类",
            "attribute_count": len(grouped["__none__"]),
            "param_count": 0,
            "product_attribute_list": grouped.pop("__none__"),
        })

    for cat_id, attr_list in grouped.items():
        items.append({
            "id": cat_id,
            "name": cat_names.get(cat_id, f"分类 {cat_id[:8]}"),
            "attribute_count": len(attr_list),
            "param_count": 0,
            "product_attribute_list": attr_list,
        })

    return success(items)


@router.post("/categories", summary="创建属性分类")
async def create_category(
    name: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    category = PmsCategory(name=name, level=0, sort=0)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return success({"id": str(category.id), "name": category.name})


@router.put("/categories/{category_id}", summary="更新属性分类名称")
async def update_category(
    category_id: UUID,
    name: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    cat = await db.get(PmsCategory, category_id)
    if not cat:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="NOT_FOUND", message=f"分类 {category_id} 不存在", status_code=404)
    cat.name = name
    await db.flush()
    return success({"id": str(cat.id), "name": cat.name})


@router.delete("/categories/{category_id}", summary="删除属性分类")
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    cat = await db.get(PmsCategory, category_id)
    if cat:
        await db.delete(cat)
        await db.flush()
    return success(message="删除成功")


# ── Generic attribute routes (registered AFTER /categories to avoid shadowing) ──


@router.get("", summary="属性分页列表")
async def list_paginated(
    category_id: UUID | None = Query(None, description="按分类筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    base = select(PmsProductAttribute)
    count_q = select(func.count(PmsProductAttribute.id))

    if category_id:
        base = base.where(PmsProductAttribute.category_id == category_id)
        count_q = count_q.where(PmsProductAttribute.category_id == category_id)

    result = await db.execute(count_q)
    total = result.scalar() or 0

    result = await db.execute(
        base.order_by(PmsProductAttribute.sort.asc())
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
