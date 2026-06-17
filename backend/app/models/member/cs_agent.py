"""客服坐席状态模型 — cs_agent_status 表

记录人工客服坐席的实时在线状态和当前负载。

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class CsAgentStatus(CommerceBase, AuditMixin):
    """客服坐席实时状态。

    每个 admin user 只有一条状态记录，通过 upsert 更新。
    """

    __tablename__ = "cs_agent_status"

    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="关联 users 表的 admin ID",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        default="offline",
        nullable=False,
        comment="坐席状态: online/offline/busy",
    )
    current_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="当前正在处理的工单ID",
    )
    max_concurrent: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="最大同时处理工单数",
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后心跳时间",
    )
    skills: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="坐席技能标签: ['refund', 'complaint', 'logistics']",
    )

    def __repr__(self) -> str:
        return f"<CsAgentStatus admin={self.admin_id!r} status={self.status!r}>"
