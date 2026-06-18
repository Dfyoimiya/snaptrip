"""create commerce member tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-26 15:00:00.000000

Phase 6 — 创建会员域 2 张表
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(name: str) -> bool:
    """Check if a table exists in the current database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("ums_member_addresses"):
        op.create_table(
            "ums_member_addresses",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("phone", sa.String(32), nullable=False),
            sa.Column("province", sa.String(32), nullable=True),
            sa.Column("city", sa.String(32), nullable=True),
            sa.Column("region", sa.String(32), nullable=True),
            sa.Column("detail_address", sa.String(200), nullable=False),
            sa.Column("post_code", sa.String(16), nullable=True),
            sa.Column("default_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_ums_member_addresses_user_id", "ums_member_addresses", ["user_id"])

    if not _table_exists("ums_member_favorites"):
        op.create_table(
            "ums_member_favorites",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_name", sa.String(200), nullable=False),
            sa.Column("product_pic", sa.String(255), nullable=True),
            sa.Column("product_price", sa.String(32), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "product_id", name="uq_user_product_fav"),
        )
    op.create_index("ix_ums_member_favs_user_id", "ums_member_favorites", ["user_id"])
    op.create_index("ix_ums_member_favs_product_id", "ums_member_favorites", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_ums_member_favs_product_id", table_name="ums_member_favorites")
    op.drop_index("ix_ums_member_favs_user_id", table_name="ums_member_favorites")
    op.drop_table("ums_member_favorites")
    op.drop_index("ix_ums_member_addresses_user_id", table_name="ums_member_addresses")
    op.drop_table("ums_member_addresses")
