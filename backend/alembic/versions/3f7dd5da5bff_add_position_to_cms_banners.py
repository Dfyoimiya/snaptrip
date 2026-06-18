"""add cms_notices table and position column to cms_banners

Revision ID: 3f7dd5da5bff
Revises: o4d5e6f7g8h9
Create Date: 2026-06-18 20:19:14.280637

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3f7dd5da5bff"
down_revision: Union[str, Sequence[str], None] = "o4d5e6f7g8h9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── cms_notices 表 ──
    op.create_table(
        "cms_notices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False, comment="公告标题"),
        sa.Column("content", sa.Text(), nullable=True, comment="公告内容（富文本HTML）"),
        sa.Column("target_type", sa.String(length=20), nullable=False, comment="目标类型: ALL/CUSTOMER/MERCHANT"),
        sa.Column("status", sa.Integer(), nullable=False, comment="0=隐藏 1=已发布"),
        sa.Column("publish_time", sa.DateTime(timezone=True), nullable=True, comment="发布时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cms_notices_is_deleted"), "cms_notices", ["is_deleted"], unique=False)

    # ── cms_banners.position 列（先 NULL 再填默认值再 NOT NULL） ──
    op.add_column("cms_banners", sa.Column("position", sa.String(length=30), nullable=True, comment="位置: HOME_TOP/HOME_MIDDLE"))
    op.execute("UPDATE cms_banners SET position = 'HOME_TOP' WHERE position IS NULL")
    op.alter_column("cms_banners", "position", nullable=False)


def downgrade() -> None:
    op.drop_column("cms_banners", "position")
    op.drop_index(op.f("ix_cms_notices_is_deleted"), table_name="cms_notices")
    op.drop_table("cms_notices")
