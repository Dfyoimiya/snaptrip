"""
【前台商城 - 秒杀 API】— /api/v1/portal/flash-promotions

Author: SnapTrip Team
Date: 2026-06-18
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.flash_service import FlashService

router = APIRouter(prefix="/portal/flash-promotions", tags=["Portal - 秒杀"])


@router.get("", summary="前台秒杀活动列表")
async def list_active_promotions(db: AsyncSession = Depends(get_db)):
    """列出当前活跃的秒杀活动（status=1，在有效时间范围内）。

    游客可访问。只返回进行中的活动。
    """
    svc = FlashService(db)
    items = await svc.list_active_portal_promotions()
    return success([i.model_dump() for i in items])


@router.get("/{promotion_id}/sessions", summary="秒杀活动场次列表")
async def list_promotion_sessions(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """列出某活动下所有场次。

    游客可访问。只返回进行中的场次。
    """
    svc = FlashService(db)
    items = await svc.list_active_portal_sessions(promotion_id=promotion_id)
    return success([i.model_dump() for i in items])


@router.get("/{promotion_id}/sessions/{session_id}/products", summary="秒杀场次商品列表")
async def list_session_products(
    promotion_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """列出某场次下的秒杀商品，含秒杀价格和剩余库存。

    游客可访问。返回秒杀商品的 flash_price、剩余 flash_stock 等信息。
    """
    svc = FlashService(db)
    items = await svc.list_active_portal_products(session_id=session_id)
    return success([i for i in items])
