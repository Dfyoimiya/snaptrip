"""
【后台管理 - 退货原因 API】— /api/v1/admin/return-reasons

Author: SnapTrip Team
Date: 2026-06-15
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order.return_reason import OmsReturnReason
from app.core.exceptions import CommerceException
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.order_setting import (
    ReturnReasonCreate,
    ReturnReasonResponse,
    ReturnReasonUpdate,
)
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/admin/return-reasons", tags=["Admin - 退货原因"])


@router.get("", summary="退货原因分页列表")
async def list_reasons(
    keyword: str | None = Query(None, description="搜索名称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    base = select(OmsReturnReason)
    count_q = select(func.count(OmsReturnReason.id))
    if keyword:
        filter_clause = OmsReturnReason.name.ilike(f"%{keyword}%")
        base = base.where(filter_clause)
        count_q = count_q.where(filter_clause)

    result = await db.execute(count_q)
    total = result.scalar() or 0

    result = await db.execute(
        base.order_by(OmsReturnReason.sort.asc(), OmsReturnReason.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    resp = PaginatedResponse.of(
        items=[ReturnReasonResponse.model_validate(r).model_dump() for r in items],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.get("/{reason_id}", summary="退货原因详情")
async def get_reason(
    reason_id: UUID,
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    reason = await db.get(OmsReturnReason, reason_id)
    if not reason:
        raise CommerceException(code="RETURN_REASON_NOT_FOUND", message="退货原因不存在", status_code=404)
    return success(ReturnReasonResponse.model_validate(reason).model_dump())


@router.post("", summary="创建退货原因", status_code=201)
async def create_reason(
    data: ReturnReasonCreate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    reason = OmsReturnReason(**data.model_dump())
    db.add(reason)
    await db.flush()
    return success(ReturnReasonResponse.model_validate(reason).model_dump())


@router.put("/{reason_id}", summary="更新退货原因")
async def update_reason(
    reason_id: UUID,
    data: ReturnReasonUpdate,
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    reason = await db.get(OmsReturnReason, reason_id)
    if not reason:
        raise CommerceException(code="RETURN_REASON_NOT_FOUND", message="退货原因不存在", status_code=404)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reason, field, value)
    await db.flush()
    return success(ReturnReasonResponse.model_validate(reason).model_dump())


@router.delete("", summary="批量删除退货原因")
async def delete_reasons(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    from sqlalchemy import delete

    await db.execute(
        delete(OmsReturnReason).where(OmsReturnReason.id.in_(ids))
    )
    await db.flush()
    return success(message="删除成功")


@router.patch("/status", summary="批量更新退货原因状态")
async def update_status(
    ids: list[UUID] = Query(..., alias="ids"),
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _u=Depends(get_current_user),
):
    await db.execute(
        update(OmsReturnReason)
        .where(OmsReturnReason.id.in_(ids))
        .values(status=status)
    )
    await db.flush()
    return success(message="更新成功")
