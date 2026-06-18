"""Role management API.

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

from app.core.rbac import require_admin_user
from app.models.menu import Menu, Resource, RoleMenu, RoleResource
from app.models.rbac import Role
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.rbac_admin import (
    AllocMenuRequest,
    AllocResourceRequest,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)

router = APIRouter(prefix="/role", tags=["System - 角色"])


@router.get("/listAll", summary="所有角色")
async def list_all(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    result = await db.execute(select(Role).order_by(Role.sort.asc()))
    roles = result.scalars().all()
    return success([RoleResponse.model_validate(r).model_dump() for r in roles])


@router.get("/list", summary="角色分页列表")
async def list_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    result = await db.execute(select(func.count(Role.id)))
    total = result.scalar() or 0

    result = await db.execute(select(Role).order_by(Role.sort.asc()).offset((page - 1) * page_size).limit(page_size))
    roles = result.scalars().all()

    resp = PaginatedResponse.of(
        items=[RoleResponse.model_validate(r).model_dump() for r in roles],
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )
    return success(resp.model_dump())


@router.post("/create", summary="创建角色")
async def create(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    role = Role(**data.model_dump())
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return success(RoleResponse.model_validate(role).model_dump())


@router.post("/update/{role_id}", summary="更新角色")
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    role = await db.get(Role, role_id)
    if not role:
        from app.core.exceptions import CommerceException

        raise CommerceException(code="ROLE_NOT_FOUND", message="角色不存在", status_code=404)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(role, k, v)
    await db.flush()
    await db.refresh(role)
    return success(RoleResponse.model_validate(role).model_dump())


@router.post("/updateStatus/{role_id}", summary="更新角色状态")
async def update_status(
    role_id: UUID,
    status: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    role = await db.get(Role, role_id)
    if not role:
        from app.core.exceptions import CommerceException

        raise CommerceException(code="ROLE_NOT_FOUND", message="角色不存在", status_code=404)
    role.status = status
    await db.flush()
    return success(message="更新成功")


@router.post("/delete", summary="批量删除角色")
async def delete_roles(
    ids: list[UUID] = Query(..., alias="ids"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    # Accepts both query param ?ids=xxx&ids=yyy and body with ids=[]
    from sqlalchemy import delete

    if ids:
        await db.execute(delete(Role).where(Role.id.in_(ids)))
    return success(message="删除成功")


@router.get("/listMenu/{role_id}", summary="获取角色菜单")
async def list_menu(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    # Return all menus for allocation UI
    result = await db.execute(select(Menu).order_by(Menu.sort.asc()))
    menus = result.scalars().all()
    return success(
        [{"id": m.id, "parent_id": m.parent_id, "title": m.title, "name": m.name, "sort": m.sort} for m in menus]
    )


@router.get("/listResource/{role_id}", summary="获取角色资源")
async def list_resource(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    result = await db.execute(select(Resource).order_by(Resource.name.asc()))
    resources = result.scalars().all()
    return success([{"id": r.id, "category_id": r.category_id, "name": r.name, "url": r.url} for r in resources])


@router.post("/allocMenu", summary="分配菜单")
async def alloc_menu(
    data: AllocMenuRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    from sqlalchemy import delete as sa_delete

    await db.execute(sa_delete(RoleMenu).where(RoleMenu.role_id == data.role_id))
    for menu_id in data.menu_ids:
        db.add(RoleMenu(role_id=data.role_id, menu_id=menu_id))
    await db.commit()
    return success(message="菜单分配成功")


@router.post("/allocResource", summary="分配资源")
async def alloc_resource(
    data: AllocResourceRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    from sqlalchemy import delete as sa_delete

    await db.execute(sa_delete(RoleResource).where(RoleResource.role_id == data.role_id))
    for resource_id in data.resource_ids:
        db.add(RoleResource(role_id=data.role_id, resource_id=resource_id))
    await db.commit()
    return success(message="资源分配成功")
