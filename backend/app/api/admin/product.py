"""
【后台管理 - 商品管理 API】— /api/v1/admin/products

覆盖 Phase 2 商品管理的 11 个接口:
  POST   /admin/products              创建商品
  PUT    /admin/products/{id}          编辑商品
  DELETE /admin/products/{id}          删除商品(软删除)
  GET    /admin/products               分页列表(多条件筛选)
  GET    /admin/products/{id}          商品详情(含SKU+属性值)
  PATCH  /admin/products/{id}/status   上架/下架
  PATCH  /admin/products/{id}/batch-status 批量上下架(简化版)
  PATCH  /admin/products/{id}/new      设为新品
  PATCH  /admin/products/{id}/recommend   设为推荐
  PATCH  /admin/products/{id}/verify   审核
  PUT    /admin/products/{id}/skus     管理SKU库存
  POST   /admin/products/{id}/sync-es  同步ES

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_admin_user
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.product import (
    ProductCreate,
    ProductListQuery,
    ProductUpdate,
    SkuCreate,
    SkuUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/admin/products", tags=["Admin - 商品管理"])


# ── CRUD ──


@router.post("", summary="创建商品", status_code=201)
async def create(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """
    创建商品 —— 一次请求传入基础信息 + SKU列表 + 属性值。
    Service 层保证事务原子性: Product + SKUs + AttributeValues 全部成功或全部回滚。
    """
    svc = ProductService(db)
    result = await svc.create(data)
    return success(result.model_dump())


@router.put("/{product_id}", summary="编辑商品")
async def update(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = ProductService(db)
    result = await svc.update(product_id, data)
    return success(result.model_dump())


@router.delete("/{product_id}", summary="删除商品")
async def delete(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = ProductService(db)
    await svc.delete(product_id)
    return success(message="删除成功")


@router.get("/{product_id}", summary="商品详情")
async def get_detail(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = ProductService(db)
    result = await svc.get_detail(product_id)
    return success(result.model_dump())


@router.get("", summary="商品分页列表")
async def list_paginated(
    keyword: str | None = Query(None, description="搜索关键词(名称/货号)"),
    brand_id: UUID | None = Query(None),
    category_id: UUID | None = Query(None),
    publish_status: int | None = Query(None, ge=0, le=1),
    verify_status: int | None = Query(None, ge=0, le=2),
    product_sn: str | None = Query(None, description="货号精确匹配"),
    sort_by: str | None = Query(None, description="排序: create_time/sale_count/price_asc/price_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    query = ProductListQuery(
        keyword=keyword,
        brand_id=brand_id,
        category_id=category_id,
        publish_status=publish_status,
        verify_status=verify_status,
        product_sn=product_sn,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    svc = ProductService(db)
    items, total = await svc.list_paginated(query)
    resp = PaginatedResponse.of(
        items=[item.model_dump() for item in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


# ── 状态操作 ──


@router.patch("/{product_id}/status", summary="上架/下架")
async def toggle_publish(
    product_id: UUID,
    status: int = Query(..., ge=0, le=1, description="0=下架 1=上架"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = ProductService(db)
    result = await svc.toggle_status(product_id, "publish_status", status)
    return success(result.model_dump())


@router.patch("/batch-status", summary="批量上下架")
async def batch_status(
    ids: list[UUID] = Query(..., min_length=1, max_length=100, description="商品ID列表"),
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """批量操作 —— 一次修改多个商品状态。参数用 Query list 而非 Body，简化前台调用"""
    from sqlalchemy import update as sql_update

    from app.models.product.product import PmsProduct

    stmt = sql_update(PmsProduct).where(PmsProduct.id.in_(ids)).values(publish_status=status)
    await db.execute(stmt)
    return success(message=f"已{'上架' if status else '下架'} {len(ids)} 个商品")


@router.patch("/{product_id}/new", summary="设为新品")
async def toggle_new(
    product_id: UUID,
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = ProductService(db)
    result = await svc.toggle_status(product_id, "new_status", status)
    return success(result.model_dump())


@router.patch("/{product_id}/recommend", summary="设为推荐")
async def toggle_recommend(
    product_id: UUID,
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = ProductService(db)
    result = await svc.toggle_status(product_id, "recommend_status", status)
    return success(result.model_dump())


@router.patch("/{product_id}/verify", summary="审核商品")
async def verify(
    product_id: UUID,
    status: int = Query(..., ge=0, le=2, description="0=待审核 1=通过 2=驳回"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    svc = ProductService(db)
    result = await svc.toggle_status(product_id, "verify_status", status)
    return success(result.model_dump())


# ── SKU 管理 ──


@router.put("/{product_id}/skus", summary="管理SKU库存")
async def manage_skus(
    product_id: UUID,
    sku_id: UUID = Query(..., description="SKU ID"),
    stock: int = Query(..., ge=0, description="新库存值"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """
    更新单个 SKU 库存 —— 同时更新商品总库存汇总。

    高并发场景下应该用:
      UPDATE pms_skus SET stock = stock + :delta WHERE id = :id
    而非先查再改 (会有 race condition)
    这里简化为直接设置绝对值，生产环境需加乐观锁
    """
    from sqlalchemy import update as sql_update

    from app.models.product.product import PmsProduct
    from app.models.product.sku import PmsSku

    # 更新 SKU 库存
    await db.execute(sql_update(PmsSku).where(PmsSku.id == sku_id).values(stock=stock))

    # 原子重算商品总库存 —— 使用子查询避免 SELECT-then-UPDATE 竞态。
    # 子查询在 UPDATE 执行时读取 SKU 表的当前已提交状态，与 UPDATE 同为
    # 一条语句，PostgreSQL 行级锁保证不会丢失其他并发 SKU 更新的写入。
    from sqlalchemy import func
    from sqlalchemy import select as sql_select

    stock_subq = (
        sql_select(func.coalesce(func.sum(PmsSku.stock), 0)).where(PmsSku.product_id == product_id).scalar_subquery()
    )
    await db.execute(sql_update(PmsProduct).where(PmsProduct.id == product_id).values(stock=stock_subq))

    return success(message="SKU库存已更新")


# ── ES 同步 ──


@router.post("/{product_id}/sync-es", summary="同步到ES")
async def sync_es(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """手动触发单个商品同步到 Elasticsearch 搜索索引"""
    from app.models.product.product import PmsProduct
    from app.services.product_service import sync_product_to_es

    product = await db.get(PmsProduct, product_id)
    if not product:
        from app.core.exceptions import ProductNotFoundError

        raise ProductNotFoundError(str(product_id))

    await sync_product_to_es(db, product)
    return success(message="ES同步成功")


# ── SKU 增/改/删 (JSON body, 区别于上面 Query 参数的库存管理) ──


@router.post("/{product_id}/skus", summary="添加SKU", status_code=201)
async def add_sku(
    product_id: UUID,
    data: SkuCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """向已有商品添加一个新 SKU。自动重算商品总库存并触发 ES 同步。"""
    svc = ProductService(db)
    result = await svc.add_sku(product_id, data)
    return success(result.model_dump())


@router.put("/{product_id}/skus/{sku_id}", summary="更新SKU")
async def update_sku(
    product_id: UUID,
    sku_id: UUID,
    data: SkuUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """更新 SKU 的价格/库存/规格/图片。只更新传入的字段。自动重算商品总库存并触发 ES 同步。"""
    svc = ProductService(db)
    result = await svc.update_sku(product_id, sku_id, data)
    return success(result.model_dump())


@router.delete("/{product_id}/skus/{sku_id}", summary="删除SKU")
async def delete_sku(
    product_id: UUID,
    sku_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """删除一个 SKU。不允许删除商品的最后一个 SKU。自动重算商品总库存并触发 ES 同步。"""
    svc = ProductService(db)
    await svc.delete_sku(product_id, sku_id)
    return success(message="SKU已删除")


# ── 属性值管理 ──


@router.put("/{product_id}/attributes", summary="更新商品属性值")
async def update_attributes(
    product_id: UUID,
    data: dict[str, str],
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """
    全量替换商品属性值 —— 先删后插 (replace 语义)。

    请求体: {"attribute_id_1": "value1", "attribute_id_2": "value2"}
    """
    svc = ProductService(db)
    result = await svc.update_attributes(product_id, data)
    return success({"product_id": str(product_id), "attribute_values": result})
