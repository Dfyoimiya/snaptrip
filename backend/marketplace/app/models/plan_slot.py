"""plan_slots 表 —— 计划时段（计划中的单个 POI 安排）。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from marketplace.app.models.base import Base

if TYPE_CHECKING:
    from marketplace.app.models.plan import Plan


class PlanSlot(Base):
    __tablename__ = "plan_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id"),
        nullable=False,
        index=True,
    )
    poi_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    time_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_status: Mapped[str] = mapped_column(String(32), nullable=False, default="tentative")
    booking_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped[Plan] = relationship("Plan", back_populates="plan_slots")

    __table_args__ = ()
