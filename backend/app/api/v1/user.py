"""用户中心 API 路由 —— 资料管理 / 计划历史 / 计划克隆。

端点:
    GET  /api/v1/user/profile          - 获取用户资料
    PUT  /api/v1/user/profile          - 更新用户资料
    GET  /api/v1/user/plans             - 分页查询计划列表
    GET  /api/v1/user/plans/{plan_id}   - 计划详情（含嵌套）
    POST /api/v1/user/plans/{plan_id}/clone - 克隆计划

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.response import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.plan import Plan
from app.models.plan_slot import PlanSlot
from app.models.user_profile import UserProfile
from app.models.users import User
from app.schemas.user import (
    PaginatedPlans,
    PlanDetailOut,
    PlanListOut,
    PlanSlotOut,
    UserProfileOut,
    UserProfileUpdateIn,
)
from app.services.user_service import trigger_preference_embedding_update

router = APIRouter(prefix="/api/v1/user", tags=["user"])


def _range_to_dict(r: asyncpg.Range | None) -> dict | None:
    if r is None:
        return None
    return {"lower": str(r.lower) if r.lower else None, "upper": str(r.upper) if r.upper else None}


# ===== 用户资料 =====


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户资料不存在")

    return success(
        data=UserProfileOut(
            nickname=profile.nickname,
            avatar_url=profile.avatar_url,
            preferences=profile.preferences or {},
            travel_style=profile.travel_style,
            home_address=profile.home_address,
            preference_embedding=profile.preference_embedding,
        ).model_dump()
    )


@router.put("/profile")
async def update_profile(
    body: UserProfileUpdateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户资料不存在")

    prefs_changed = False

    if body.nickname is not None:
        profile.nickname = body.nickname
    if body.avatar_url is not None:
        profile.avatar_url = body.avatar_url
    if body.preferences is not None:
        if profile.preferences != body.preferences:
            prefs_changed = True
        profile.preferences = body.preferences
    if body.travel_style is not None:
        profile.travel_style = body.travel_style
    if body.home_address is not None:
        profile.home_address = body.home_address

    await db.flush()
    await db.commit()

    if prefs_changed:
        trigger_preference_embedding_update(str(current_user.id))

    return success(
        data=UserProfileOut(
            nickname=profile.nickname,
            avatar_url=profile.avatar_url,
            preferences=profile.preferences or {},
            travel_style=profile.travel_style,
            home_address=profile.home_address,
            preference_embedding=profile.preference_embedding,
        ).model_dump(),
        message="资料已更新",
    )


# ===== 计划列表 =====


@router.get("/plans")
async def list_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    group_type: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    offset = (page - 1) * page_size

    conditions = [Plan.user_id == current_user.id]
    if status_filter:
        conditions.append(Plan.status == status_filter)
    if group_type:
        conditions.append(Plan.group_type == group_type)

    total_q = select(func.count(Plan.id)).where(*conditions)
    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    rows_q = select(Plan).where(*conditions).order_by(Plan.created_at.desc()).offset(offset).limit(page_size)
    rows_result = await db.execute(rows_q)
    plans = rows_result.scalars().all()

    items = [
        PlanListOut(
            id=str(p.id),
            title=p.title,
            status=p.status,
            date_range=_range_to_dict(p.date_range),
            group_type=p.group_type,
            created_at=p.created_at,
        )
        for p in plans
    ]

    return success(data=PaginatedPlans(items=items, total=total, page=page, page_size=page_size).model_dump())


# ===== 计划详情 =====


@router.get("/plans/{plan_id}")
async def get_plan_detail(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Plan)
        .options(
            selectinload(Plan.plan_slots),
            selectinload(Plan.checkpoints),
            selectinload(Plan.plan_adjustments),
        )
        .where(Plan.id == plan_id, Plan.user_id == current_user.id)
    )
    plan = result.unique().scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计划不存在")

    _utc_min = datetime.min.replace(tzinfo=UTC)
    slots = sorted(plan.plan_slots, key=lambda s: s.time_start if s.time_start else _utc_min)
    checkpoints = sorted(plan.checkpoints, key=lambda c: c.version)
    adjustments = sorted(plan.plan_adjustments, key=lambda a: a.created_at if a.created_at else _utc_min)

    return success(
        data=PlanDetailOut(
            id=str(plan.id),
            title=plan.title,
            status=plan.status,
            date_range=_range_to_dict(plan.date_range),
            group_type=plan.group_type,
            created_at=plan.created_at,
            slots=[
                PlanSlotOut(
                    id=str(s.id),
                    poi_id=s.poi_id,
                    time_start=s.time_start,
                    time_end=s.time_end,
                    slot_status=s.slot_status,
                    booking_ref=s.booking_ref,
                    buffer_minutes=s.buffer_minutes,
                )
                for s in slots
            ],
            checkpoints=[
                {
                    "id": str(c.id),
                    "version": c.version,
                    "slots_snapshot": c.slots_snapshot,
                    "consensus_status": c.consensus_status,
                    "created_at": str(c.created_at),
                }
                for c in checkpoints
            ],
            adjustments=[
                {
                    "id": str(a.id),
                    "trigger_reason": a.trigger_reason,
                    "original_slots": a.original_slots,
                    "adjusted_slots": a.adjusted_slots,
                    "user_confirmed": a.user_confirmed,
                    "created_at": str(a.created_at),
                }
                for a in adjustments
            ],
        ).model_dump()
    )


# ===== 计划克隆 =====


@router.post("/plans/{plan_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Plan).options(selectinload(Plan.plan_slots)).where(Plan.id == plan_id, Plan.user_id == current_user.id)
    )
    original = result.unique().scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计划不存在")

    new_plan_id = uuid.uuid4()
    new_plan = Plan(
        id=new_plan_id,
        user_id=current_user.id,
        title=f"Copy of {original.title}",
        status="draft",
        date_range=original.date_range,
        group_type=original.group_type,
    )
    db.add(new_plan)

    for slot in original.plan_slots:
        new_slot = PlanSlot(
            id=uuid.uuid4(),
            plan_id=new_plan_id,
            poi_id=slot.poi_id,
            time_start=slot.time_start,
            time_end=slot.time_end,
            slot_status="tentative",
            booking_ref=None,
            buffer_minutes=slot.buffer_minutes,
            actual_end=None,
        )
        db.add(new_slot)

    await db.commit()

    return success(
        data={"plan_id": str(new_plan_id), "title": new_plan.title},
        message="计划克隆成功",
    )
