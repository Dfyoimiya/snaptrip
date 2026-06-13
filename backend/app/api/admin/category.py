"""
【后台管理 - 商品分类 API】— /api/v1/admin/categories

知识点速查:
  - FastAPI APIRouter: 模块化路由, prefix 定义该文件所有路由的公共前缀
  - Depends(get_db): FastAPI 依赖注入, 自动调用 get_db 获取 session 并 yield 给路由
    如果不使用 Depends: 需要手动管理数据库连接, 创建/关闭/异常回滚都要写
  - Depends(get_current_user): JWT 认证依赖, 从 Authorization Header 解析用户
  - Response 格式: 统一用 success() 包装 `{code:0, message:"success", data:...}`
  - 为什么路由只负责"参数提取+调用Service+返回结果"？
    "瘦路由、胖服务" —— 路由不写业务逻辑, 方便后续单独测试 Service 层

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.product import (
    CategoryCreate,
    CategoryUpdate,
)
from app.services.category_service import CategoryService
from marketplace.app.core.security import get_current_user  # JWT 认证

router = APIRouter(prefix="/admin/categories", tags=["Admin - 商品分类"])


@router.post("", summary="创建分类")
async def create(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    result = await svc.create(data)
    return success(result.model_dump())


@router.put("/{category_id}", summary="编辑分类")
async def update(
    category_id: UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    result = await svc.update(category_id, data)
    return success(result.model_dump())


@router.delete("/{category_id}", summary="删除分类")
async def delete(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    await svc.delete(category_id)
    return success(message="删除成功")


@router.get("/tree", summary="分类树形结构")
async def get_tree(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取完整分类树 —— 用于商品编辑页选择分类"""
    svc = CategoryService(db)
    tree = await svc.get_tree()
    return success([node.model_dump() for node in tree])


@router.get("/{category_id}", summary="分类详情")
async def get_detail(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    result = await svc.get_by_id(category_id)
    return success(result.model_dump())


@router.get("", summary="分类分页列表")
async def list_paginated(
    parent_id: UUID | None = Query(None, description="父分类ID筛选"),
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


@router.patch("/{category_id}/status", summary="切换分类状态")
async def toggle_status(
    category_id: UUID,
    field: str = Query(..., description="状态字段: nav_status 或 show_status"),
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    result = await svc.toggle_status(category_id, field, status)
    return success(result.model_dump())


@router.patch("/{category_id}/sort", summary="修改分类排序")
async def update_sort(
    category_id: UUID,
    sort: int = Query(..., ge=0),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    svc = CategoryService(db)
    result = await svc.toggle_status(category_id, "sort", sort)
    return success(result.model_dump())
