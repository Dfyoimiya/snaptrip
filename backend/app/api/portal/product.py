"""
【前台商城 - 商品浏览 API】— /api/v1/portal/products

混合搜索: ES BM25 + pgvector 融合, 支持价格区间过滤 + 个性化 boost。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.product import PortalProductDetailResponse
from app.services.product_service import ProductService
from app.utils.display import format_sale_count

router = APIRouter(prefix="/portal/products", tags=["Portal - 商品浏览"])


def _resolve_user_id(request: Request) -> UUID | None:
    """从 Authorization header 解析 user_id (可选认证)。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        from marketplace.app.core.security import decode_access_token

        token = auth.removeprefix("Bearer ").strip()
        payload = decode_access_token(token)
        sub = payload.get("sub", "")
        return UUID(sub) if sub else None
    except Exception:
        return None


def _get_hybrid_search(request: Request):
    """初始化 HybridSearchService (含 QueryUnderstandingService)。"""
    from snaptrip_shared.db.session import AsyncSessionLocal

    from app.search.client import get_search_client
    from app.services.hybrid_search_service import HybridSearchService
    from app.services.query_understanding_service import QueryUnderstandingService
    from app.services.search_personalization_service import SearchPersonalizationService

    es = get_search_client()
    vector = request.app.state.vector_search_service
    memory = request.app.state.memory
    # LLM adapter from app state (may be None if LLM init failed)
    llm = getattr(request.app.state, "llm_adapter", None)

    personalization = SearchPersonalizationService(
        db_factory=AsyncSessionLocal,
        memory=memory,
    )
    query_understanding = QueryUnderstandingService(
        llm_adapter=llm,
        memory=memory,
    )
    cf = request.app.state.cf_service if hasattr(request.app.state, "cf_service") else None
    return HybridSearchService(
        es_client=es,
        vector_service=vector,
        cf_service=cf,
        query_understanding=query_understanding,
        personalization_service=personalization,
    )


@router.get("", summary="商品搜索/分类浏览（混合搜索）")
async def search(
    request: Request,
    keyword: str | None = Query(None, description="搜索关键词"),
    category_id: UUID | None = Query(None, description="分类筛选"),
    brand_id: UUID | None = Query(None, description="品牌筛选"),
    min_price: float | None = Query(None, ge=0, description="最低价格"),
    max_price: float | None = Query(None, ge=0, description="最高价格"),
    sort_by: str = Query("default", description="排序: default/sales/new/price_asc/price_desc"),
    match_mode: Literal["contains", "smart"] = Query("smart", description="匹配模式: contains/smart"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: UUID | None = Depends(_resolve_user_id),
):
    """前台商品搜索 —— ES BM25 + pgvector 融合 + 个性化。

    过滤策略:
      1. publish_status=1 (已上架)
      2. verify_status=1 (审核通过)
      3. is_deleted=False (未软删除)
    """
    hybrid = _get_hybrid_search(request)
    hybrid._db = db

    result = await hybrid.search(
        keyword=keyword,
        category_id=str(category_id) if category_id else None,
        brand_id=str(brand_id) if brand_id else None,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
        user_id=user_id,
        match_mode=match_mode,
    )

    items = result["items"]

    # 转为前端兼容格式
    product_items = [
        {
            "id": item.get("id", item.get("product_id", "")),
            "name": item.get("name", ""),
            "subTitle": item.get("sub_title", ""),
            "price": item.get("price", 0),
            "originalPrice": item.get("original_price"),
            "saleCount": item.get("sale_count", 0),
            "saleCountDisplay": format_sale_count(item.get("sale_count", 0)),
            "defaultPic": item.get("image_url", item.get("default_pic", "")),
            "brandName": item.get("brand_name", ""),
            "categoryId": item.get("category_id", ""),
            "stock": item.get("stock", 0),
            "score": item.get("score", 0),
            "_searchMethod": result.get("method", ""),
        }
        for item in items
    ]

    resp = PaginatedResponse.of(
        items=product_items,
        total=result["total"],
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
    request: Request,
    category_id: UUID,
    min_price: float | None = Query(None, ge=0, description="最低价格"),
    max_price: float | None = Query(None, ge=0, description="最高价格"),
    sort_by: str = Query("default", description="排序: default/sales/new/price_asc/price_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: UUID | None = Depends(_resolve_user_id),
):
    """按分类浏览商品 —— 支持价格区间过滤。"""
    hybrid = _get_hybrid_search(request)
    hybrid._db = db

    result = await hybrid.search(
        keyword=None,
        category_id=str(category_id),
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
        user_id=user_id,
    )

    items = result["items"]
    product_items = [
        {
            "id": item.get("id", item.get("product_id", "")),
            "name": item.get("name", ""),
            "price": item.get("price", 0),
            "saleCount": item.get("sale_count", 0),
            "saleCountDisplay": format_sale_count(item.get("sale_count", 0)),
            "defaultPic": item.get("image_url", item.get("default_pic", "")),
            "brandName": item.get("brand_name", ""),
            "categoryId": item.get("category_id", ""),
            "stock": item.get("stock", 0),
        }
        for item in items
    ]

    resp = PaginatedResponse.of(
        items=product_items,
        total=result["total"],
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())
