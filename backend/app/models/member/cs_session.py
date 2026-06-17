"""客服会话记忆模型 — cs_session_summaries 表

C2B 智能客服系统的长期记忆存储：每个 CS 会话结束后由 LLM 压缩为结构化摘要。

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class CsSessionSummary(CommerceBase, AuditMixin):
    """客服会话摘要 —— LLM 压缩后的长期记忆。

    每次 CS 会话结束时生成一条摘要，供未来会话快速加载上下文。
    """

    __tablename__ = "cs_session_summaries"

    session_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="会话ID"
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="用户ID (匿名为空)"
    )
    intent: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True,
        comment="客服意图: cs_after_sales/cs_complaint/cs_inquiry",
    )
    summary_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="LLM 生成的会话摘要"
    )
    resolution_status: Mapped[str] = mapped_column(
        String(32), default="unknown", nullable=False,
        comment="解决状态: resolved/escalated/abandoned/unknown",
    )
    satisfaction_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="满意度 1-5"
    )
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="关联工单ID"
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="关联订单ID"
    )
    conversation_turns: Mapped[int] = mapped_column(
        Integer, default=0, comment="对话轮数"
    )
    tools_called: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="调用的工具列表"
    )
    key_entities: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="关键实体: {order_ids, product_ids, amounts, ...}"
    )
    emotion_trajectory: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="情绪轨迹: angry→calm, neutral→satisfied, ...",
    )

    def __repr__(self) -> str:
        return f"<CsSessionSummary session={self.session_id!r} status={self.resolution_status!r}>"
