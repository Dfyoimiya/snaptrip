"""plan_runs 表 —— 一次计划运行的审计记录。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from marketplace.app.models.base import Base


class PlanRun(Base):
    __tablename__ = "plan_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    plan_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    thread_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    graph_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    final_status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    debug: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
