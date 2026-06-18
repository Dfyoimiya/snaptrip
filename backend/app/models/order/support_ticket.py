"""客服工单模型 — oms_support_tickets 表

C2B 智能客服系统中的人工升级工单。

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class OmsSupportTicket(CommerceBase, AuditMixin):
    """客服工单 —— 当 AI Agent 无法解决问题时升级到人工坐席。"""

    __tablename__ = "oms_support_tickets"

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="关联订单ID"
    )
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True, comment="会员ID")
    type: Mapped[str] = mapped_column(
        String(32),
        default="inquiry",
        nullable=False,
        index=True,
        comment="工单类型: complaint/refund/inquiry/other",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="open",
        nullable=False,
        index=True,
        comment="工单状态: open/in_progress/resolved/closed",
    )
    priority: Mapped[str] = mapped_column(
        String(16),
        default="normal",
        nullable=False,
        comment="优先级: normal/urgent/critical",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="工单标题")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="问题描述")
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理结果")
    satisfaction_score: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="满意度评分 1-5")
    escalated_to: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="处理人")
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="指派的坐席 admin ID"
    )
    sla_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="SLA 响应截止时间"
    )
    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="首次人工响应时间"
    )
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="工单标签: ['urgent', 'vip']")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="解决时间")

    def __repr__(self) -> str:
        return f"<OmsSupportTicket type={self.type!r} status={self.status!r}>"
