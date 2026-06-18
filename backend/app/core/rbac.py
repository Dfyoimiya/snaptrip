"""RBAC dependencies for protected admin APIs."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from snaptrip_shared.db.session import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission, Role, RolePermission, UserRole
from marketplace.app.core.security import get_current_user
from marketplace.app.models.users import User

SUPER_ADMIN_ROLES = {"super_admin"}
ADMIN_ROLE_PREFIXES = ("admin",)
ADMIN_ROLE_SUFFIXES = ("_admin", "_manager", "_agent")


async def _load_active_role_names(db: AsyncSession, user_id) -> set[str]:
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, Role.status == 1)
    )
    return {name for name in result.scalars().all() if name}


def _is_admin_role(role_name: str) -> bool:
    return (
        role_name in SUPER_ADMIN_ROLES
        or role_name.startswith(ADMIN_ROLE_PREFIXES)
        or role_name.endswith(ADMIN_ROLE_SUFFIXES)
    )


async def require_admin_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Allow only users with an active admin-like role."""
    role_names = await _load_active_role_names(db, current_user.id)
    if any(_is_admin_role(role_name) for role_name in role_names):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="需要后台管理权限",
    )


def require_permissions(*permission_names: str) -> Callable:
    """FastAPI dependency factory requiring at least one explicit permission."""

    async def _dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        role_names = await _load_active_role_names(db, current_user.id)
        if role_names & SUPER_ADMIN_ROLES:
            return current_user
        if not permission_names:
            if any(_is_admin_role(role_name) for role_name in role_names):
                return current_user
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要后台管理权限")

        result = await db.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == current_user.id,
                Role.status == 1,
                Permission.status == 1,
                Permission.name.in_(permission_names),
            )
        )
        granted = set(result.scalars().all())
        if granted:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )

    return _dependency


def require_roles(*role_names: str) -> Callable:
    """FastAPI dependency factory requiring one of the provided active roles."""

    async def _dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        active_roles = await _load_active_role_names(db, current_user.id)
        allowed = set(role_names)
        if active_roles & (allowed | SUPER_ADMIN_ROLES):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )

    return _dependency
