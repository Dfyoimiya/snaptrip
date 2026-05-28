"""RBAC 权限模型 —— 角色 / 权限 / 角色权限关联 / 用户角色关联。

参考 mall 的 ums_role / ums_permission / ums_role_permission_relation / ums_admin_role_relation。

设计:
  - 多对多: 角色 ↔ 权限 (RolePermission 中间表)
  - 用户 ↔ 角色 (UserRole 关联 — 用户可拥有多个角色)

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, CommerceBase


class Role(CommerceBase, AuditMixin):
    """角色表 —— ums_roles"""

    __tablename__ = "ums_roles"

    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="角色名称",
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="角色描述")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="1=启用 0=禁用")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")

    # 关联
    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="ums_role_permissions",
        back_populates="roles",
        lazy="selectin",
    )


class Permission(CommerceBase, AuditMixin):
    """权限表 —— ums_permissions"""

    __tablename__ = "ums_permissions"

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="权限名称, 如 product:create")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="权限描述")
    resource: Mapped[str] = mapped_column(String(128), nullable=False, comment="资源路径, 如 /admin/products")
    method: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="HTTP 方法, 如 GET/POST/PUT/DELETE")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="1=启用 0=禁用")

    # 关联
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="ums_role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )


class RolePermission(CommerceBase):
    """角色-权限关联表 —— ums_role_permissions"""

    __tablename__ = "ums_role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ums_roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ums_permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UserRole(CommerceBase, AuditMixin):
    """用户-角色关联表 —— ums_user_roles"""

    __tablename__ = "ums_user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="关联 users 表的 id",
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ums_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[Role] = relationship("Role", lazy="joined")
