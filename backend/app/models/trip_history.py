"""trip_history 表 —— 用户历史出行记录与满意度反馈。

存储每次完成的出行计划及逐 slot 评分，支持：
- 情景记忆语义检索（pgvector cosine similarity）
- 偏好衰减建模（近期出行权重高于历史出行）
- 协同过滤信号提取（相似用户喜欢什么）

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TripHistory(Base):
    __tablename__ = "trip_history"

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
    plan_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    city: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    scene_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="solo",
        comment="family/couple/solo/friends/business",
    )
    guest_count: Mapped[int] = mapped_column(Integer, default=1)
    slots_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment="Snapshot of PlanSlot list as JSON"
    )
    total_cost: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    # Overall satisfaction 1-5
    satisfaction_rating: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    # Per-slot feedback: [{"slot_index": 0, "rating": 4, "comment": "..."}, ...]
    slot_feedback: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True
    )
    # Embedding for semantic retrieval (derived from city + scene_type + keywords)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536), nullable=True,
        comment="Semantic embedding of trip characteristics for similarity search"
    )
    # Rejection log: POI types or specific POIs user disliked
    rejected_poi_ids: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    rejected_types: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    __table_args__ = ()

    def to_summary(self) -> dict:
        """Compact representation for memory injection."""
        return {
            "trip_id": str(self.id),
            "city": self.city,
            "scene_type": self.scene_type,
            "guest_count": self.guest_count,
            "total_cost": self.total_cost,
            "rating": self.satisfaction_rating,
            "slot_count": len(self.slots_json.get("slots", [])),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
