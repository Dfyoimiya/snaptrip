"""Menu & Resource models for RBAC admin panel.

Author: SnapTrip Team
Date: 2026-06-09
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String
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
