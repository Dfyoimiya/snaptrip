"""create order settings, return reasons, return applies tables

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-06-15 12:00:00.000000

Phase 2 — 创建订单设置/退货原因/退货申请 3 张表
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "h8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "g7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(name: str) -> bool:
    """Check if a table exists in the current database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ── oms_order_settings ──
    if not _table_exists("oms_order_settings"):
        op.create_table(
            "oms_order_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("flash_order_overtime", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("normal_order_overtime", sa.Integer(), nullable=False, server_default="120"),
            sa.Column("confirm_overtime", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("finish_overtime", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("comment_overtime", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── oms_return_reasons ──
    if not _table_exists("oms_return_reasons"):
        op.create_table(
            "oms_return_reasons",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_oms_return_reasons_status", "oms_return_reasons", ["status"])

    # ── oms_return_applies ──
    if not _table_exists("oms_return_applies"):
        op.create_table(
            "oms_return_applies",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_sn", sa.String(64), nullable=True),
            sa.Column("member_username", sa.String(64), nullable=True),
            sa.Column("return_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("return_name", sa.String(100), nullable=True),
            sa.Column("return_phone", sa.String(32), nullable=True),
            sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("handle_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("product_pic", sa.String(255), nullable=True),
            sa.Column("product_name", sa.String(200), nullable=True),
            sa.Column("product_brand", sa.String(100), nullable=True),
            sa.Column("product_attr", sa.Text(), nullable=True),
            sa.Column("product_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("product_real_price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("reason", sa.String(255), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("proof_pics", sa.Text(), nullable=True),
            sa.Column("handle_note", sa.Text(), nullable=True),
            sa.Column("handle_man", sa.String(100), nullable=True),
            sa.Column("receive_man", sa.String(100), nullable=True),
            sa.Column("receive_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("receive_note", sa.Text(), nullable=True),
            sa.Column("company_address_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_oms_return_applies_order_id", "oms_return_applies", ["order_id"])
    op.create_index("ix_oms_return_applies_status", "oms_return_applies", ["status"])


def downgrade() -> None:
    op.drop_index("ix_oms_return_applies_status", table_name="oms_return_applies")
    op.drop_index("ix_oms_return_applies_order_id", table_name="oms_return_applies")
    op.drop_table("oms_return_applies")
    op.drop_index("ix_oms_return_reasons_status", table_name="oms_return_reasons")
    op.drop_table("oms_return_reasons")
    op.drop_table("oms_order_settings")
