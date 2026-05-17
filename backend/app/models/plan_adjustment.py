"""plan_adjustments 表 —— 计划变更记录。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.plan import Plan


class PlanAdjustment(Base):
    __tablename__ = "plan_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id"),
        nullable=False,
    )
    trigger_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    original_slots: Mapped[dict] = mapped_column(JSON, nullable=False)
    adjusted_slots: Mapped[dict] = mapped_column(JSON, nullable=False)
    user_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    plan: Mapped[Plan] = relationship("Plan", back_populates="plan_adjustments")

    __table_args__ = ()
