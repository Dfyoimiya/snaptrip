"""Admin user management API — UMS Admin CRUD.

Author: SnapTrip Team
Date: 2026-06-09
"""

from __future__ import annotations

import uuid as _uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Role, UserRole
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.rbac_admin import (
    AdminRegisterRequest,
    AdminRoleUpdateRequest,
    AdminUpdateRequest,
    AdminUserResponse,
    RoleResponse,
)
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["System - 用户管理"])


async def _get_user_roles(db: AsyncSession, user_id: UUID) -> list[RoleResponse]:
    result = await db.execute(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    roles = result.scalars().all()
    return [RoleResponse.model_validate(r) for r in roles]


async def _build_admin_response(db: AsyncSession, row) -> dict:
    roles = await _get_user_roles(db, row.id)
    return {
        "id": row.id,
        "email": row.email,
        "is_active": row.is_active,
        "created_at": row.created_at,
        "roles": [r.model_dump() for r in roles],
    }


@router.get("/list", summary="管理员列表")
async def list_admins(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from sqlalchemy import text

    result = await db.execute(text("SELECT count(*) FROM users"))
    total = result.scalar() or 0

    result = await db.execute(
        text("SELECT id, email, is_active, created_at FROM users ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        {"limit": page_size, "offset": (page - 1) * page_size},
    )
    rows = result.fetchall()

    items = []
    for row in rows:
        items.append(await _build_admin_response(db, row))

    resp = PaginatedResponse.of(
        items=items,
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/register", summary="注册管理员")
async def register_admin(
    data: AdminRegisterRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from snaptrip_shared.core.security import hash_password
    from sqlalchemy import text
    user_id = __uuid.uuid4()
    hashed = hash_password(data.password)

    await db.execute(
        text("INSERT INTO users (id, email, hashed_password, is_active) VALUES (:id, :email, :hashed, true)"),
        {"id": user_id, "email": data.email, "hashed": hashed},
    )
    for role_id in data.role_ids:
        ur = UserRole(id=_uuid.uuid4(), user_id=user_id, role_id=role_id)
        db.add(ur)
    await db.flush()

    return success({"id": str(user_id), "email": data.email})


@router.post("/update/{user_id}", summary="更新管理员")
async def update_admin(
    user_id: UUID,
    data: AdminUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from sqlalchemy import text

    if data.email is not None or data.is_active is not None or data.password is not None:
        set_clauses = []
        params: dict = {"id": user_id}
        if data.email is not None:
            set_clauses.append("email = :email")
            params["email"] = data.email
        if data.is_active is not None:
            set_clauses.append("is_active = :is_active")
            params["is_active"] = data.is_active
        if data.password is not None:
            from snaptrip_shared.core.security import hash_password
            set_clauses.append("hashed_password = :hashed")
            params["hashed"] = hash_password(data.password)
        if set_clauses:
            await db.execute(
                text(f"UPDATE users SET {', '.join(set_clauses)} WHERE id = :id"),
                params,
            )

    if data.role_ids is not None:
        from sqlalchemy import delete
        await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
        for role_id in data.role_ids:
            db.add(UserRole(id=_uuid.uuid4(), user_id=user_id, role_id=role_id))

    await db.flush()
    return success(message="更新成功")


@router.post("/updateStatus/{user_id}", summary="更新管理员状态")
async def update_status(
    user_id: UUID,
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from sqlalchemy import text
    await db.execute(
        text("UPDATE users SET is_active = :status WHERE id = :id"),
        {"status": bool(status), "id": user_id},
    )
    await db.flush()
    return success(message="更新成功")


@router.post("/delete/{user_id}", summary="删除管理员")
async def delete_admin(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from sqlalchemy import text, delete
    await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    await db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    await db.flush()
    return success(message="删除成功")


@router.get("/role/{admin_id}", summary="获取管理员角色")
async def get_admin_roles(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    roles = await _get_user_roles(db, admin_id)
    return success([r.model_dump() for r in roles])


@router.post("/role/update", summary="更新管理员角色")
async def update_admin_roles(
    data: AdminRoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from sqlalchemy import delete
    await db.execute(delete(UserRole).where(UserRole.user_id == data.admin_id))
    for role_id in data.role_ids:
        db.add(UserRole(id=_uuid.uuid4(), user_id=data.admin_id, role_id=role_id))
    await db.flush()
    return success(message="角色更新成功")
