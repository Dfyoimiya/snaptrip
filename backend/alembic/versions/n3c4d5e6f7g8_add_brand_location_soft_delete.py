"""add brand location fields and soft delete

Revision ID: n3c4d5e6f7g8
Revises: m2b3c4d5e6f7
Create Date: 2026-06-18

This migration:
  1. Adds latitude / longitude / address / phone to pms_brands (merchant store info)
  2. Adds is_deleted / deleted_at to pms_brands (soft delete support)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "n3c4d5e6f7g8"
down_revision: str | None = "m2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Location / contact columns ──
    op.add_column("pms_brands", sa.Column("latitude", sa.Float, nullable=True, comment="门店纬度"))
    op.add_column("pms_brands", sa.Column("longitude", sa.Float, nullable=True, comment="门店经度"))
    op.add_column(
        "pms_brands",
        sa.Column("address", sa.String(255), nullable=True, comment="门店地址"),
    )
    op.add_column(
        "pms_brands",
        sa.Column("phone", sa.String(32), nullable=True, comment="联系电话"),
    )

    # ── 2. Soft delete columns ──
    op.add_column(
        "pms_brands",
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false"), comment="软删除标记"),
    )
    op.add_column(
        "pms_brands",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
    )
    op.create_index("ix_pms_brands_is_deleted", "pms_brands", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_pms_brands_is_deleted", table_name="pms_brands")
    op.drop_column("pms_brands", "deleted_at")
    op.drop_column("pms_brands", "is_deleted")
    op.drop_column("pms_brands", "phone")
    op.drop_column("pms_brands", "address")
    op.drop_column("pms_brands", "longitude")
    op.drop_column("pms_brands", "latitude")
