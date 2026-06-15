"""
【前台商城 - 商品浏览 API】— /api/v1/portal/products

不需要 JWT 认证 (游客也能浏览商品), 只返回上架+审核通过的商品。

知识点速查：
  - 为什么门户接口不需要 get_current_user？
    电商前台允许未登录浏览，认证是可选的 (optional auth)
    如果需要"猜你喜欢"等个性化推荐，可以用 Depends(get_current_user_or_none)

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
from app.schemas.product import PortalProductDetailResponse, PortalProductResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/portal/products", tags=["Portal - 商品浏览"])


@router.get("", summary="商品搜索/分类浏览")
async def search(
    keyword: str | None = Query(None, description="搜索关键词"),
    category_id: UUID | None = Query(None, description="分类筛选"),
    brand_id: UUID | None = Query(None, description="品牌筛选"),
    sort_by: str = Query("default", description="排序: default/sales/new/price_asc/price_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    # 注意: 游客可访问, 不加 _current_user=Depends(get_current_user)
):
    """
    前台商品搜索 —— 组合关键词+分类+品牌+价格区间+排序。

    过滤策略:
      1. publish_status=1 (已上架)
      2. verify_status=1 (审核通过)
      3. is_deleted=False (未软删除)
    这三个过滤条件在 Service 层硬编码，路由不需要传参，保证安全。
    """
    svc = ProductService(db)
    items, total = await svc.list_portal(
        keyword=keyword,
        category_id=category_id,
        brand_id=brand_id,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    resp = PaginatedResponse.of(
        items=[PortalProductResponse(**item.model_dump()).model_dump() for item in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{product_id}", summary="商品详情")
async def get_detail(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """商品详情页 —— 返回基础信息 + SKU列表 + 属性值（已排除后台管理字段）。"""
    svc = ProductService(db)
    result = await svc.get_detail(product_id)
    portal_result = PortalProductDetailResponse(**result.model_dump())
    return success(portal_result.model_dump())


@router.get("/category/{category_id}", summary="按分类浏览")
async def by_category(
    category_id: UUID,
    sort_by: str = Query("default", description="排序: default/sales/new/price_asc/price_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """按分类浏览商品 —— /category/{id} 的组合，方便前端路由"""
    svc = ProductService(db)
    items, total = await svc.list_portal(
        category_id=category_id,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    resp = PaginatedResponse.of(
        items=[PortalProductResponse(**item.model_dump()).model_dump() for item in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())
