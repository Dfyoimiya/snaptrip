"""
【后台管理 - 退货申请 API】— /api/v1/admin/return-applies

Author: SnapTrip Team
Date: 2026-06-15
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CommerceException
from app.core.rbac import require_admin_user
from app.models.order.order import OmsOrder, OmsOrderOperateLog
from app.models.order.return_apply import OmsReturnApply
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.order import OrderStatus
from app.schemas.order_setting import ReturnApplyResponse, ReturnApplyUpdateStatus

router = APIRouter(prefix="/admin/return-applies", tags=["Admin - 退货申请"])


@router.get("", summary="退货申请分页列表")
async def list_applies(
    id: UUID | None = Query(None, description="退货申请ID"),
    status: int | None = Query(None, ge=0, le=3, description="处理状态"),
    create_time: str | None = Query(None, description="申请时间 (开始)"),
    handle_man: str | None = Query(None, description="处理人"),
    handle_time: str | None = Query(None, description="处理时间 (开始)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    base = select(OmsReturnApply)
    count_q = select(func.count(OmsReturnApply.id))

    if id:
        base = base.where(OmsReturnApply.id == id)
        count_q = count_q.where(OmsReturnApply.id == id)
    if status is not None:
        base = base.where(OmsReturnApply.status == status)
        count_q = count_q.where(OmsReturnApply.status == status)
    if create_time:
        try:
            start = datetime.fromisoformat(create_time)
            base = base.where(OmsReturnApply.created_at >= start)
            count_q = count_q.where(OmsReturnApply.created_at >= start)
        except ValueError:
            pass
    if handle_man:
        base = base.where(OmsReturnApply.handle_man.ilike(f"%{handle_man}%"))
        count_q = count_q.where(OmsReturnApply.handle_man.ilike(f"%{handle_man}%"))
    if handle_time:
        try:
            start = datetime.fromisoformat(handle_time)
            base = base.where(OmsReturnApply.handle_time >= start)
            count_q = count_q.where(OmsReturnApply.handle_time >= start)
        except ValueError:
            pass

    result = await db.execute(count_q)
    total = result.scalar() or 0

    result = await db.execute(
        base.order_by(OmsReturnApply.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()

    resp = PaginatedResponse.of(
        items=[ReturnApplyResponse.model_validate(a).model_dump() for a in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{apply_id}", summary="退货申请详情")
async def get_apply(
    apply_id: UUID,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    apply = await db.get(OmsReturnApply, apply_id)
    if not apply:
        raise CommerceException(code="RETURN_APPLY_NOT_FOUND", message="退货申请不存在", status_code=404)
    return success(ReturnApplyResponse.model_validate(apply).model_dump())


@router.patch("/{apply_id}/status", summary="更新退货申请状态")
async def update_status(
    apply_id: UUID,
    data: ReturnApplyUpdateStatus,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    apply = await db.get(OmsReturnApply, apply_id)
    if not apply:
        raise CommerceException(code="RETURN_APPLY_NOT_FOUND", message="退货申请不存在", status_code=404)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(apply, field, value)
    if data.status in (1, 2, 3):
        from datetime import UTC

        apply.handle_time = datetime.now(UTC)

    # 同步订单状态: 退款完成 → 订单标记为已退款；拒绝 → 订单恢复为已完成
    if apply.order_id is not None:
        if data.status == 3:
            # 已退款: 订单 → REFUNDED(7)
            order = await db.get(OmsOrder, apply.order_id)
            if order is not None:
                old_status = order.status
                order.status = OrderStatus.REFUNDED
                db.add(
                    OmsOrderOperateLog(
                        order_id=order.id,
                        operate_man=_u.email,
                        order_status_before=old_status,
                        order_status_after=OrderStatus.REFUNDED,
                        note=f"退货申请 {apply_id} 已退款",
                    )
                )
        elif data.status == 2:
            # 已拒绝: 订单 → COMPLETED(4)
            order = await db.get(OmsOrder, apply.order_id)
            if order is not None:
                old_status = order.status
                order.status = OrderStatus.COMPLETED
                db.add(
                    OmsOrderOperateLog(
                        order_id=order.id,
                        operate_man=_u.email,
                        order_status_before=old_status,
                        order_status_after=OrderStatus.COMPLETED,
                        note=f"退货申请 {apply_id} 已拒绝",
                    )
                )

    await db.flush()
    return success(ReturnApplyResponse.model_validate(apply).model_dump())


@router.delete("", summary="批量删除退货申请")
async def delete_applies(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    await db.execute(delete(OmsReturnApply).where(OmsReturnApply.id.in_(ids)))
    await db.flush()
    return success(message="删除成功")
