"""
【后台管理 - 订单设置 API】— /api/v1/admin/order-settings

单行配置表: 不存在时自动创建默认值。

Author: SnapTrip Team
Date: 2026-06-15
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_admin_user
from app.models.order.setting import OmsOrderSetting
from app.schemas.order_setting import OrderSettingResponse, OrderSettingUpdate

router = APIRouter(prefix="/admin/order-settings", tags=["Admin - 订单设置"])

_DEFAULT_ID = "00000000-0000-0000-0000-000000000001"


async def _get_or_create_setting(db: AsyncSession) -> OmsOrderSetting:
    """获取订单设置，不存在则创建一个默认值设置。"""
    result = await db.execute(select(OmsOrderSetting).limit(1))
    setting = result.scalars().first()
    if not setting:
        setting = OmsOrderSetting(id=_DEFAULT_ID)
        db.add(setting)
        await db.flush()
    return setting


@router.get("/{setting_id}", summary="获取订单设置")
async def get_setting(
    setting_id: str,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    result = await db.execute(select(OmsOrderSetting).limit(1))
    setting = result.scalars().first()
    if not setting:
        setting = OmsOrderSetting(id=_DEFAULT_ID)
        db.add(setting)
        await db.flush()
    return success(OrderSettingResponse.model_validate(setting).model_dump())


@router.put("/{setting_id}", summary="更新订单设置")
async def update_setting(
    setting_id: str,
    data: OrderSettingUpdate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    setting = await _get_or_create_setting(db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(setting, field, value)
    await db.flush()
    return success(OrderSettingResponse.model_validate(setting).model_dump())
