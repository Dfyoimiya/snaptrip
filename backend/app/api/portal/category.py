"""
【前台商城 - 分类浏览 API】— /api/v1/portal/categories

Author: SnapTrip Team
Date: 2026-06-14
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.category_service import CategoryService

router = APIRouter(prefix="/portal/categories", tags=["Portal - 分类"])


@router.get("", summary="分类列表")
async def list_categories(
    parent_id: UUID | None = Query(None, description="父分类ID，不传则返回顶级分类"),
    db: AsyncSession = Depends(get_db),
):
    """前台分类列表 —— 只返回显示状态的分类"""
    svc = CategoryService(db)
    items, _ = await svc.list_paginated(parent_id=parent_id, page=1, page_size=200)
    return success([item.model_dump() for item in items])


@router.get("/tree", summary="分类树")
async def category_tree(db: AsyncSession = Depends(get_db)):
    """前台分类树 —— 导航栏使用"""
    svc = CategoryService(db)
    tree = await svc.get_tree()
    return success([node.model_dump() for node in tree])
