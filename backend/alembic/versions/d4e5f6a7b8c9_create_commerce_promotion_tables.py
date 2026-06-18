"""create commerce promotion tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-26 13:00:00.000000

Phase 4 — 创建营销域 5 张表
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(name: str) -> bool:
    """Check if a table exists in the current database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ── sms_coupons ──
    if not _table_exists("sms_coupons"):
        op.create_table(
            "sms_coupons",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("type", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("use_type", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("min_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("count", sa.Integer(), nullable=False),
            sa.Column("publish_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("receive_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("per_limit", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("member_level", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("note", sa.String(200), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── sms_coupon_histories ──
    if not _table_exists("sms_coupon_histories"):
        op.create_table(
            "sms_coupon_histories",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("coupon_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("coupon_name", sa.String(100), nullable=False),
            sa.Column("coupon_type", sa.Integer(), nullable=False),
            sa.Column("coupon_use_type", sa.Integer(), nullable=False),
            sa.Column("coupon_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("coupon_min_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("use_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("use_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("order_sn", sa.String(64), nullable=True),
            sa.Column("receive_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expire_time", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["coupon_id"], ["sms_coupons.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_sms_coupon_histories_coupon_id", "sms_coupon_histories", ["coupon_id"])
    op.create_index("ix_sms_coupon_histories_user_id", "sms_coupon_histories", ["user_id"])

    # ── sms_flash_promotions ──
    if not _table_exists("sms_flash_promotions"):
        op.create_table(
            "sms_flash_promotions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("note", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── sms_flash_sessions ──
    if not _table_exists("sms_flash_sessions"):
        op.create_table(
            "sms_flash_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("promotion_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["promotion_id"], ["sms_flash_promotions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_sms_flash_sessions_promo_id", "sms_flash_sessions", ["promotion_id"])

    # ── sms_flash_promotion_products ──
    if not _table_exists("sms_flash_promotion_products"):
        op.create_table(
            "sms_flash_promotion_products",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("flash_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("flash_stock", sa.Integer(), nullable=False),
            sa.Column("flash_limit", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["session_id"], ["sms_flash_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_sms_flash_products_session_id", "sms_flash_promotion_products", ["session_id"])
    op.create_index("ix_sms_flash_products_product_id", "sms_flash_promotion_products", ["product_id"])
    op.create_index("ix_sms_flash_products_sku_id", "sms_flash_promotion_products", ["sku_id"])


def downgrade() -> None:
    op.drop_index("ix_sms_flash_products_sku_id", table_name="sms_flash_promotion_products")
    op.drop_index("ix_sms_flash_products_product_id", table_name="sms_flash_promotion_products")
    op.drop_index("ix_sms_flash_products_session_id", table_name="sms_flash_promotion_products")
    op.drop_table("sms_flash_promotion_products")
    op.drop_index("ix_sms_flash_sessions_promo_id", table_name="sms_flash_sessions")
    op.drop_table("sms_flash_sessions")
    op.drop_table("sms_flash_promotions")
    op.drop_index("ix_sms_coupon_histories_user_id", table_name="sms_coupon_histories")
    op.drop_index("ix_sms_coupon_histories_coupon_id", table_name="sms_coupon_histories")
    op.drop_table("sms_coupon_histories")
    op.drop_table("sms_coupons")
