"""客服通知模型 — cs_notifications 表

人工坐席的通知消息：新工单、新消息、SLA 告警等。

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class CsNotification(CommerceBase, AuditMixin):
    """客服通知 —— 推送给 admin 坐席的实时通知。

    类型:
      - new_ticket: 新工单
      - new_message: 用户发来新消息
      - sla_warning: SLA 即将超时
      - sla_breach: SLA 已超时
      - ticket_closed: 工单已关闭
      - ticket_assigned: 工单已指派给你
    """

    __tablename__ = "cs_notifications"

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="接收通知的管理员 ID",
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="通知类型: new_ticket/new_message/sla_warning/sla_breach/ticket_closed/ticket_assigned",
    )
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="关联工单ID",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="通知标题",
    )
    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="通知正文",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否已读",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="阅读时间",
    )

    def __repr__(self) -> str:
        return f"<CsNotification type={self.type!r} recipient={self.recipient_id!r}>"
