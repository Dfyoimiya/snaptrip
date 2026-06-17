"""create CS agent models: support tickets, session summaries, messages, agent status, notifications

Revision ID: l1a2b3c4d5e6
Revises: k1f2g3h4i5j6
Create Date: 2026-06-17

This migration:
  1. Creates oms_support_tickets table (Phase 2)
  2. Creates cs_session_summaries table (Phase 3)
  3. Creates cs_conversation_messages table (Phase 4)
  4. Creates cs_agent_status table (Phase 4)
  5. Creates cs_notifications table (Phase 4)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "l1a2b3c4d5e6"
down_revision: str | None = "k1f2g3h4i5j6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. oms_support_tickets (Phase 2) ──
    op.create_table(
        "oms_support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(32), nullable=False, server_default="inquiry",
                  comment="工单类型: complaint/refund/inquiry/other"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open",
                  comment="工单状态: open/in_progress/resolved/closed"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal",
                  comment="优先级: normal/urgent/critical"),
        sa.Column("title", sa.String(255), nullable=False, comment="工单标题"),
        sa.Column("description", sa.Text, nullable=True, comment="问题描述"),
        sa.Column("resolution", sa.Text, nullable=True, comment="处理结果"),
        sa.Column("satisfaction_score", sa.Integer, nullable=True, comment="满意度评分 1-5"),
        sa.Column("escalated_to", sa.String(100), nullable=True, comment="处理人"),
        sa.Column("assigned_agent_id", postgresql.UUID(as_uuid=True), nullable=True,
                  comment="指派的坐席 admin ID"),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True,
                  comment="SLA 响应截止时间"),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True,
                  comment="首次人工响应时间"),
        sa.Column("tags", postgresql.JSON, nullable=True, comment="工单标签"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True, comment="解决时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_oms_support_tickets_order_id", "oms_support_tickets", ["order_id"])
    op.create_index("ix_oms_support_tickets_member_id", "oms_support_tickets", ["member_id"])
    op.create_index("ix_oms_support_tickets_type", "oms_support_tickets", ["type"])
    op.create_index("ix_oms_support_tickets_status", "oms_support_tickets", ["status"])
    op.create_index("ix_oms_support_tickets_assigned_agent_id", "oms_support_tickets",
                    ["assigned_agent_id"])

    # ── 2. cs_session_summaries (Phase 3) ──
    op.create_table(
        "cs_session_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(64), nullable=False, comment="会话ID"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, comment="用户ID"),
        sa.Column("intent", sa.String(32), nullable=True,
                  comment="客服意图: cs_after_sales/cs_complaint/cs_inquiry"),
        sa.Column("summary_text", sa.Text, nullable=False, comment="LLM 生成的会话摘要"),
        sa.Column("resolution_status", sa.String(32), nullable=False, server_default="unknown",
                  comment="解决状态: resolved/escalated/abandoned/unknown"),
        sa.Column("satisfaction_score", sa.Integer, nullable=True, comment="满意度 1-5"),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True, comment="关联工单ID"),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True, comment="关联订单ID"),
        sa.Column("conversation_turns", sa.Integer, nullable=False, server_default="0",
                  comment="对话轮数"),
        sa.Column("tools_called", postgresql.JSON, nullable=True, comment="调用的工具列表"),
        sa.Column("key_entities", postgresql.JSON, nullable=True,
                  comment="关键实体: {order_ids, product_ids, amounts, ...}"),
        sa.Column("emotion_trajectory", sa.String(32), nullable=True,
                  comment="情绪轨迹: angry→calm"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_cs_session_summaries_session_id", "cs_session_summaries", ["session_id"])
    op.create_index("ix_cs_session_summaries_user_id", "cs_session_summaries", ["user_id"])
    op.create_index("ix_cs_session_summaries_intent", "cs_session_summaries", ["intent"])

    # ── 3. cs_conversation_messages (Phase 4) ──
    op.create_table(
        "cs_conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False,
                  comment="关联工单ID"),
        sa.Column("sender_type", sa.String(16), nullable=False,
                  comment="发送者类型: user/agent/system"),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=True,
                  comment="发送者 ID"),
        sa.Column("content", sa.Text, nullable=False, comment="消息正文"),
        sa.Column("content_type", sa.String(16), nullable=False, server_default="text",
                  comment="内容类型: text/markdown/system_event"),
        sa.Column("metadata", postgresql.JSON, nullable=True, comment="附加数据"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_cs_conversation_messages_ticket_id", "cs_conversation_messages",
                    ["ticket_id"])
    op.create_foreign_key(
        "fk_cs_conversation_messages_ticket_id",
        "cs_conversation_messages", "oms_support_tickets",
        ["ticket_id"], ["id"],
        ondelete="CASCADE",
    )

    # ── 4. cs_agent_status (Phase 4) ──
    op.create_table(
        "cs_agent_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=False,
                  comment="关联 users 表的 admin ID"),
        sa.Column("status", sa.String(16), nullable=False, server_default="offline",
                  comment="坐席状态: online/offline/busy"),
        sa.Column("current_ticket_id", postgresql.UUID(as_uuid=True), nullable=True,
                  comment="当前正在处理的工单ID"),
        sa.Column("max_concurrent", sa.Integer, nullable=False, server_default="3",
                  comment="最大同时处理工单数"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True,
                  comment="最后心跳时间"),
        sa.Column("skills", postgresql.JSON, nullable=True, comment="坐席技能标签"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_cs_agent_status_admin_id", "cs_agent_status", ["admin_id"], unique=True)
    op.create_foreign_key(
        "fk_cs_agent_status_admin_id",
        "cs_agent_status", "users",
        ["admin_id"], ["id"],
        ondelete="CASCADE",
    )

    # ── 5. cs_notifications (Phase 4) ──
    op.create_table(
        "cs_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False,
                  comment="接收通知的管理员 ID"),
        sa.Column("type", sa.String(32), nullable=False,
                  comment="通知类型: new_ticket/new_message/sla_warning/sla_breach"),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True,
                  comment="关联工单ID"),
        sa.Column("title", sa.String(255), nullable=False, comment="通知标题"),
        sa.Column("body", sa.Text, nullable=True, comment="通知正文"),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false",
                  comment="是否已读"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True, comment="阅读时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_cs_notifications_recipient_id", "cs_notifications", ["recipient_id"])
    op.create_index("ix_cs_notifications_ticket_id", "cs_notifications", ["ticket_id"])
    op.create_index("ix_cs_notifications_type", "cs_notifications", ["type"])
    op.create_foreign_key(
        "fk_cs_notifications_recipient_id",
        "cs_notifications", "users",
        ["recipient_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_table("cs_notifications")
    op.drop_table("cs_agent_status")
    op.drop_table("cs_conversation_messages")
    op.drop_table("cs_session_summaries")
    op.drop_table("oms_support_tickets")
