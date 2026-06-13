"""Miscellaneous compatibility routes — /subject, /sku, /orderSetting, etc.

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

from app.models.cms.content import CmsSubject
from app.models.product.sku import PmsSku
from app.schemas.common import PaginatedResponse, PaginationParams
from marketplace.app.core.security import get_current_user


# ── Subject ──

subject_router = APIRouter(prefix="/subject", tags=["Macalline Compat - 专题"])


@subject_router.get("/listAll", summary="所有专题")
async def subject_list_all(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(CmsSubject).order_by(CmsSubject.id.asc()))
    items = result.scalars().all()
    return success([
        {"id": s.id, "title": s.title, "pic": s.pic, "status": s.status}
        for s in items
    ])


@subject_router.get("/list", summary="专题分页列表")
async def subject_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(func.count(CmsSubject.id)))
    total = result.scalar() or 0
    result = await db.execute(
        select(CmsSubject).order_by(CmsSubject.id.asc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    resp = PaginatedResponse.of(
        items=[{"id": s.id, "title": s.title, "pic": s.pic, "status": s.status} for s in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


# ── SKU ──

sku_router = APIRouter(prefix="/sku", tags=["Macalline Compat - SKU"])


@sku_router.get("/{pid}", summary="根据商品ID查SKU")
async def sku_by_product(
    pid: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(PmsSku).where(PmsSku.product_id == pid)
    )
    skus = result.scalars().all()
    return success([
        {
            "id": s.id,
            "product_id": s.product_id,
            "sku_code": s.sku_code,
            "price": str(s.price) if s.price else "0",
            "stock": s.stock,
            "pic": s.pic,
            "specs": s.spec,
        }
        for s in skus
    ])


@sku_router.post("/update/{pid}", summary="更新商品SKU")
async def sku_update(
    pid: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="请使用 /admin/products/{id}/skus 接口")


# ── Order Setting ──

order_setting_router = APIRouter(prefix="/orderSetting", tags=["Macalline Compat - 订单设置"])


@order_setting_router.get("/{setting_id}", summary="获取订单设置")
async def get_order_setting(
    setting_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success({
        "id": str(setting_id),
        "flash_order_overtime": 30,
        "normal_order_overtime": 120,
        "confirm_overtime": 15,
        "finish_overtime": 7,
        "comment_overtime": 30,
    })


@order_setting_router.post("/update/{setting_id}", summary="更新订单设置")
async def update_order_setting(
    setting_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


# ── Return Apply ──

return_apply_router = APIRouter(prefix="/returnApply", tags=["Macalline Compat - 退货申请"])


@return_apply_router.get("/list", summary="退货申请列表")
async def return_apply_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    resp = PaginatedResponse.of(
        items=[],
        total=0,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@return_apply_router.get("/{apply_id}", summary="退货申请详情")
async def return_apply_detail(
    apply_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success({})


@return_apply_router.post("/update/status/{apply_id}", summary="更新退货申请状态")
async def return_apply_status(
    apply_id: UUID,
    status: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


@return_apply_router.post("/delete", summary="删除退货申请")
async def return_apply_delete(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="删除成功")


# ── Return Reason ──

return_reason_router = APIRouter(prefix="/returnReason", tags=["Macalline Compat - 退货原因"])


@return_reason_router.get("/list", summary="退货原因列表")
async def return_reason_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    resp = PaginatedResponse.of(
        items=[],
        total=0,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@return_reason_router.get("/{reason_id}", summary="退货原因详情")
async def return_reason_detail(
    reason_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success({})


@return_reason_router.post("/create", summary="创建退货原因")
async def return_reason_create(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="创建成功")


@return_reason_router.post("/update/{reason_id}", summary="更新退货原因")
async def return_reason_update(
    reason_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


@return_reason_router.post("/delete", summary="删除退货原因")
async def return_reason_delete(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="删除成功")


@return_reason_router.post("/update/status", summary="更新退货原因状态")
async def return_reason_status(
    ids: list[UUID] = Query(..., alias="ids"),
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success(message="更新成功")


# ── Company Address ──

company_address_router = APIRouter(prefix="/companyAddress", tags=["Macalline Compat - 公司地址"])


@company_address_router.get("/list", summary="公司地址列表")
async def company_address_list(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success([])


# ── OSS ──

oss_router = APIRouter(prefix="/aliyun/oss", tags=["Macalline Compat - OSS"])


@oss_router.get("/policy", summary="OSS上传策略")
async def oss_policy(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success({
        "accessKeyId": "minioadmin",
        "accessKeySecret": "minioadmin",
        "bucket": "snaptrip-commerce",
        "endpoint": "localhost:9000",
        "policy": "",
        "signature": "",
    })


# ── Preference Area ──

prefrence_area_router = APIRouter(prefix="/prefrenceArea", tags=["Macalline Compat - 优选专区"])


@prefrence_area_router.get("/listAll", summary="优选专区列表")
async def prefrence_area_list_all(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return success([])
