"""
【前台商城 - 首页聚合 API】— /api/v1/portal/home

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cms_service import StatsService

router = APIRouter(prefix="/portal/home", tags=["Portal - 首页"])


@router.get("", summary="首页聚合")
async def home_page(db: AsyncSession = Depends(get_db)):
    """首页聚合 —— Banner + 新品 + 推荐商品 + 专题，游客可访问"""
    svc = StatsService(db)
    result = await svc.get_homepage()
    return success(result.model_dump())
