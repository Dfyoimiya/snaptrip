"""客服聊天消息模型 — cs_conversation_messages 表

工单维度的对话记录，支持 user/agent/system 三种发送者类型。

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class CsConversationMessage(CommerceBase, AuditMixin):
    """客服聊天消息 —— 每条消息属于一个工单。

    发送者类型:
      - user: C 端用户
      - agent: 人工坐席 (admin user)
      - system: 系统自动消息 (如 "坐席已加入" / "工单已关闭")
    """

    __tablename__ = "cs_conversation_messages"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oms_support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联工单ID",
    )
    sender_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="发送者类型: user/agent/system",
    )
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="发送者 ID (user ID 或 admin ID)",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息正文",
    )
    content_type: Mapped[str] = mapped_column(
        String(16),
        default="text",
        nullable=False,
        comment="内容类型: text/markdown/system_event",
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="附加数据: {attachment_urls, ...}",
    )

    def __repr__(self) -> str:
        return f"<CsConversationMessage ticket={self.ticket_id!r} sender={self.sender_type!r}>"
