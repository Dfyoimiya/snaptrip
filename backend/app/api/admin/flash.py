"""
【后台管理 - 秒杀管理 API】— /api/v1/admin/flash-promotions

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
from app.schemas.promotion import (
    FlashProductCreate,
    FlashProductUpdate,
    FlashPromotionCreate,
    FlashPromotionUpdate,
    FlashSessionCreate,
    FlashSessionUpdate,
)
from app.services.flash_service import FlashService
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/admin/flash-promotions", tags=["Admin - 秒杀"])


# ── 活动 ──


@router.post("", summary="创建秒杀活动", status_code=201)
async def create_promo(data: FlashPromotionCreate, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = FlashService(db)
    result = await svc.create_promotion(data)
    return success(result.model_dump())


@router.put("/{promo_id}", summary="编辑秒杀活动")
async def update_promo(
    promo_id: UUID, data: FlashPromotionUpdate, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)
):
    svc = FlashService(db)
    result = await svc.update_promotion(promo_id, data)
    return success(result.model_dump())


@router.delete("/{promo_id}", summary="删除秒杀活动")
async def delete_promo(promo_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)):
    svc = FlashService(db)
    await svc.delete_promotion(promo_id)
    return success(message="删除成功")


@router.get("", summary="秒杀活动列表")
async def list_promos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = FlashService(db)
    items, total = await svc.list_promotions(page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items], total=total, params=PaginationParams(page=page, page_size=page_size)
    )
    return success(resp.model_dump())


# ── 场次列表 ──
# 注意: GET /sessions 必须在 GET /{promo_id}/sessions 之前定义，
# 否则 FastAPI 会将 "sessions" 误匹配为 promo_id UUID


@router.get("/sessions", summary="所有场次列表")
async def list_all_sessions(
    promotion_id: UUID | None = Query(None, alias="promotionId"),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = FlashService(db)
    items = await svc.list_sessions(promo_id=promotion_id)
    return success([i.model_dump() for i in items])


@router.get("/{promo_id}/sessions", summary="秒杀活动下的场次列表")
async def list_sessions(
    promo_id: UUID,
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = FlashService(db)
    items = await svc.list_sessions(promo_id=promo_id)
    return success([i.model_dump() for i in items])


# ── 场次 ──


@router.post("/{promo_id}/sessions", summary="添加秒杀场次", status_code=201)
async def create_session(
    promo_id: UUID, data: FlashSessionCreate, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)
):
    data.promotion_id = promo_id
    svc = FlashService(db)
    result = await svc.create_session(data)
    return success(result.model_dump())


@router.put("/{promo_id}/sessions/{session_id}", summary="编辑场次")
async def update_session(
    promo_id: UUID,
    session_id: UUID,
    data: FlashSessionUpdate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = FlashService(db)
    result = await svc.update_session(session_id, data)
    return success(result.model_dump())


@router.delete("/{promo_id}/sessions/{session_id}", summary="删除场次")
async def delete_session(
    promo_id: UUID, session_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)
):
    svc = FlashService(db)
    await svc.delete_session(session_id)
    return success(message="删除成功")


@router.patch("/{promo_id}/sessions/{session_id}/status", summary="启用/停用场次")
async def toggle_session(
    promo_id: UUID,
    session_id: UUID,
    status: int = Query(..., ge=0, le=2),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = FlashService(db)
    result = await svc.toggle_session_status(session_id, status)
    return success(result.model_dump())


# ── 秒杀商品 ──


@router.post("/{promo_id}/sessions/{session_id}/products", summary="添加秒杀商品", status_code=201)
async def add_product(
    promo_id: UUID,
    session_id: UUID,
    data: FlashProductCreate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    data.session_id = session_id
    svc = FlashService(db)
    result = await svc.add_product(data)
    return success(result.model_dump())


@router.get("/{promo_id}/sessions/{session_id}/products", summary="秒杀商品列表")
async def list_products(
    promo_id: UUID,
    session_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = FlashService(db)
    items, total = await svc.list_products(session_id=session_id, page=page, page_size=page_size)
    resp = PaginatedResponse.of(
        items=[i.model_dump() for i in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.put("/{promo_id}/sessions/{session_id}/products/{product_id}", summary="编辑秒杀商品")
async def update_product(
    promo_id: UUID,
    session_id: UUID,
    product_id: UUID,
    data: FlashProductUpdate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    svc = FlashService(db)
    result = await svc.update_product(product_id, data)
    return success(result.model_dump())


@router.delete("/{promo_id}/sessions/{session_id}/products/{product_id}", summary="删除秒杀商品")
async def delete_product(
    promo_id: UUID, session_id: UUID, product_id: UUID, db: AsyncSession = Depends(get_db), _u=Depends(get_current_user)
):
    svc = FlashService(db)
    await svc.delete_product(product_id)
    return success(message="删除成功")
