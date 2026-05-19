"""plans 表 —— 活动计划。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import DATERANGE, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.checkpoint import Checkpoint
    from app.models.plan_adjustment import PlanAdjustment
    from app.models.plan_slot import PlanSlot
    from app.models.users import User


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    date_range: Mapped[Any] = mapped_column(DATERANGE, nullable=False, index=True)
    group_type: Mapped[str] = mapped_column(String(32), nullable=False, default="solo")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship("User", back_populates="plans")
    plan_slots: Mapped[list[PlanSlot]] = relationship("PlanSlot", back_populates="plan")
    checkpoints: Mapped[list[Checkpoint]] = relationship("Checkpoint", back_populates="plan")
    plan_adjustments: Mapped[list[PlanAdjustment]] = relationship("PlanAdjustment", back_populates="plan")

    __table_args__ = ()
