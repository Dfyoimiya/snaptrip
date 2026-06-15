"""Menu management API.

Author: SnapTrip Team
Date: 2026-06-09
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu import Menu
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.rbac_admin import MenuCreate, MenuNode, MenuUpdate
from marketplace.app.core.security import get_current_user

router = APIRouter(prefix="/menu", tags=["System - 菜单"])


def _build_tree(menus: Sequence[Menu], parent_id: UUID | None = None) -> list[MenuNode]:
    children = [m for m in menus if m.parent_id == parent_id]
    result: list[MenuNode] = []
    for m in sorted(children, key=lambda x: x.sort):
        node = MenuNode(
            id=m.id,
            parent_id=m.parent_id,
            title=m.title,
            name=m.name,
            icon=m.icon,
            sort=m.sort,
            hidden=m.hidden,
            level=m.level,
            children=_build_tree(menus, m.id),
        )
        result.append(node)
    return result


@router.get("/treeList", summary="菜单树")
async def tree_list(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(select(Menu).order_by(Menu.sort.asc()))
    menus = result.scalars().all()
    tree = _build_tree(menus)
    return success([node.model_dump() for node in tree])


@router.get("/list/{parent_id}", summary="按父级查子菜单")
async def list_by_parent(
    parent_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Menu).where(Menu.parent_id == parent_id).order_by(Menu.sort.asc())
    )
    menus = result.scalars().all()
    return success([MenuNode.model_validate(m).model_dump() for m in menus])


@router.post("/create", summary="创建菜单")
async def create(
    data: MenuCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    menu = Menu(**data.model_dump())
    db.add(menu)
    await db.flush()
    await db.refresh(menu)
    return success(MenuNode.model_validate(menu).model_dump())


@router.post("/update/{menu_id}", summary="更新菜单")
async def update_menu(
    menu_id: UUID,
    data: MenuUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    menu = await db.get(Menu, menu_id)
    if not menu:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="MENU_NOT_FOUND", message="菜单不存在", status_code=404)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(menu, k, v)
    await db.flush()
    await db.refresh(menu)
    return success(MenuNode.model_validate(menu).model_dump())


@router.post("/delete/{menu_id}", summary="删除菜单")
async def delete_menu(
    menu_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    menu = await db.get(Menu, menu_id)
    if not menu:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="MENU_NOT_FOUND", message="菜单不存在", status_code=404)
    await db.delete(menu)
    return success(message="删除成功")


@router.get("/{menu_id}", summary="菜单详情")
async def get_menu(
    menu_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    menu = await db.get(Menu, menu_id)
    if not menu:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="MENU_NOT_FOUND", message="菜单不存在", status_code=404)
    return success(MenuNode.model_validate(menu).model_dump())


@router.post("/updateHidden/{menu_id}", summary="切换菜单隐藏状态")
async def toggle_hidden(
    menu_id: UUID,
    hidden: int = Query(..., ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    menu = await db.get(Menu, menu_id)
    if not menu:
        from app.core.exceptions import CommerceException
        raise CommerceException(code="MENU_NOT_FOUND", message="菜单不存在", status_code=404)
    menu.hidden = hidden
    await db.flush()
    return success(message="更新成功")
