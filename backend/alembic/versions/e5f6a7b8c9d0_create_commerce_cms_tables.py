"""create commerce cms tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-26 14:00:00.000000

Phase 5 — 创建 CMS 内容域 3 张表
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    """Check if a table exists in the current database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("cms_banners"):
        op.create_table(
            'cms_banners',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('title', sa.String(100), nullable=False),
            sa.Column('pic', sa.String(255), nullable=False),
            sa.Column('url', sa.String(500), nullable=True),
            sa.Column('sort', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('status', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _table_exists("cms_subjects"):
        op.create_table(
            'cms_subjects',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('summary', sa.String(500), nullable=True),
            sa.Column('pic', sa.String(255), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('category_name', sa.String(100), nullable=True),
            sa.Column('status', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('recommend_status', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _table_exists("cms_helps"):
        op.create_table(
            'cms_helps',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('title', sa.String(100), nullable=False),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('category_name', sa.String(100), nullable=True),
            sa.Column('status', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('sort', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade() -> None:
    op.drop_table('cms_helps')
    op.drop_table('cms_subjects')
    op.drop_table('cms_banners')
