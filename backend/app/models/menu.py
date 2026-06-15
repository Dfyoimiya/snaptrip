"""Menu & Resource models for RBAC admin panel.

Author: SnapTrip Team
Date: 2026-06-09
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import CommerceBase


class Menu(CommerceBase):
    __tablename__ = "ums_menus"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hidden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ResourceCategory(CommerceBase):
    __tablename__ = "ums_resource_categories"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    resources: Mapped[list["Resource"]] = relationship(back_populates="category", lazy="selectin")


class Resource(CommerceBase):
    __tablename__ = "ums_resources"

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ums_resource_categories.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    category: Mapped[ResourceCategory | None] = relationship(back_populates="resources", lazy="joined")


class RoleMenu(CommerceBase):
    """角色-菜单关联表 —— ums_role_menus"""

    __tablename__ = "ums_role_menus"
    __table_args__ = (
        UniqueConstraint("role_id", "menu_id", name="uq_role_menu"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ums_roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ums_menus.id", ondelete="CASCADE"),
        primary_key=True,
    )


class RoleResource(CommerceBase):
    """角色-资源关联表 —— ums_role_resources"""

    __tablename__ = "ums_role_resources"
    __table_args__ = (
        UniqueConstraint("role_id", "resource_id", name="uq_role_resource"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ums_roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ums_resources.id", ondelete="CASCADE"),
        primary_key=True,
    )
