"""create member behaviors, search logs, product embeddings tables

Revision ID: i9d0e1f2a3b4
Revises: e7ff688378bb
Create Date: 2026-06-16 12:00:00.000000

Phase 3 — 创建用户行为追踪、搜索日志、商品向量嵌入 3 张表
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = 'i9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'e7ff688378bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    """Check if a table exists in the current database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ── ums_member_behaviors ──
    if not _table_exists("ums_member_behaviors"):
        op.create_table(
            'ums_member_behaviors',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('session_id', sa.String(64), nullable=True),
            sa.Column('behavior_type', sa.String(32), nullable=False),
            sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('item_type', sa.String(32), nullable=True),
            sa.Column('metadata', postgresql.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
    op.create_index('ix_ums_member_behaviors_user_id', 'ums_member_behaviors', ['user_id'])
    op.create_index('ix_ums_member_behaviors_session_id', 'ums_member_behaviors', ['session_id'])
    op.create_index('ix_ums_member_behaviors_behavior_type', 'ums_member_behaviors', ['behavior_type'])
    op.create_index('ix_ums_member_behaviors_item_id', 'ums_member_behaviors', ['item_id'])
    # 复合索引: 按用户+行为类型+时间查询 (最常用查询模式)
    op.create_index(
        'ix_ums_member_behaviors_user_behavior_created',
        'ums_member_behaviors',
        ['user_id', 'behavior_type', 'created_at'],
    )

    # ── ums_member_search_logs ──
    if not _table_exists("ums_member_search_logs"):
        op.create_table(
            'ums_member_search_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('session_id', sa.String(64), nullable=True),
            sa.Column('keyword', sa.String(200), nullable=False),
            sa.Column('filters', postgresql.JSON(), nullable=True),
            sa.Column('result_count', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
    op.create_index('ix_ums_member_search_logs_user_id', 'ums_member_search_logs', ['user_id'])
    op.create_index('ix_ums_member_search_logs_session_id', 'ums_member_search_logs', ['session_id'])

    # ── pms_product_embeddings ──
    if not _table_exists("pms_product_embeddings"):
        op.create_table(
            'pms_product_embeddings',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('embedding', Vector(1536), nullable=False),
            sa.Column('model_name', sa.String(64), nullable=False, server_default='text-embedding-3-small'),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['product_id'], ['pms_products.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('product_id', name='uq_pms_product_embeddings_product_id'),
        )
    op.create_index('ix_pms_product_embeddings_product_id', 'pms_product_embeddings', ['product_id'])


def downgrade() -> None:
    op.drop_index('ix_pms_product_embeddings_product_id', table_name='pms_product_embeddings')
    op.drop_table('pms_product_embeddings')
    op.drop_index('ix_ums_member_search_logs_session_id', table_name='ums_member_search_logs')
    op.drop_index('ix_ums_member_search_logs_user_id', table_name='ums_member_search_logs')
    op.drop_table('ums_member_search_logs')
    op.drop_index('ix_ums_member_behaviors_user_behavior_created', table_name='ums_member_behaviors')
    op.drop_index('ix_ums_member_behaviors_item_id', table_name='ums_member_behaviors')
    op.drop_index('ix_ums_member_behaviors_behavior_type', table_name='ums_member_behaviors')
    op.drop_index('ix_ums_member_behaviors_session_id', table_name='ums_member_behaviors')
    op.drop_index('ix_ums_member_behaviors_user_id', table_name='ums_member_behaviors')
    op.drop_table('ums_member_behaviors')
