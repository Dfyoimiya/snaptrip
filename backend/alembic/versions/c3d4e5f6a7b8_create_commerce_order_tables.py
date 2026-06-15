"""create commerce order tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-26 12:00:00.000000

Phase 3 — 创建订单域 4 张表
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    """Check if a table exists in the current database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ── oms_cart_items ──
    if not _table_exists("oms_cart_items"):
        op.create_table(
            'oms_cart_items',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('product_name', sa.String(200), nullable=False),
            sa.Column('product_pic', sa.String(255), nullable=True),
            sa.Column('sku_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('sku_code', sa.String(64), nullable=False),
            sa.Column('spec', sa.String(255), nullable=False),
            sa.Column('price', sa.Numeric(10, 2), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('checked', sa.Integer(), nullable=False, server_default='1'),
            sa.PrimaryKeyConstraint('id'),
        )
    op.create_index('ix_oms_cart_items_user_id', 'oms_cart_items', ['user_id'])
    op.create_index('ix_oms_cart_items_product_id', 'oms_cart_items', ['product_id'])
    op.create_index('ix_oms_cart_items_sku_id', 'oms_cart_items', ['sku_id'])

    # ── oms_orders ──
    if not _table_exists("oms_orders"):
        op.create_table(
            'oms_orders',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('order_sn', sa.String(64), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('member_username', sa.String(64), nullable=False),
            sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('pay_amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('freight_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
            sa.Column('discount_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
            sa.Column('coupon_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('pay_type', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('payment_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('pay_order_sn', sa.String(64), nullable=True),
            sa.Column('delivery_company', sa.String(64), nullable=True),
            sa.Column('delivery_sn', sa.String(64), nullable=True),
            sa.Column('delivery_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('receiver_name', sa.String(100), nullable=False),
            sa.Column('receiver_phone', sa.String(32), nullable=False),
            sa.Column('receiver_province', sa.String(32), nullable=True),
            sa.Column('receiver_city', sa.String(32), nullable=True),
            sa.Column('receiver_region', sa.String(32), nullable=True),
            sa.Column('receiver_detail_address', sa.String(200), nullable=False),
            sa.Column('receiver_post_code', sa.String(16), nullable=True),
            sa.Column('status', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('auto_confirm_day', sa.Integer(), nullable=False, server_default='15'),
            sa.Column('confirm_status', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('delete_status', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('note', sa.String(500), nullable=True),
            sa.Column('admin_note', sa.String(500), nullable=True),
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('order_sn', name='uq_oms_orders_sn'),
        )
    op.create_index('ix_oms_orders_user_id', 'oms_orders', ['user_id'])
    op.create_index('ix_oms_orders_status', 'oms_orders', ['status'])
    op.create_index('ix_oms_orders_sn', 'oms_orders', ['order_sn'], unique=True)

    # ── oms_order_items ──
    if not _table_exists("oms_order_items"):
        op.create_table(
            'oms_order_items',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('order_sn', sa.String(64), nullable=False),
            sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('product_name', sa.String(200), nullable=False),
            sa.Column('product_pic', sa.String(255), nullable=True),
            sa.Column('sku_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('sku_code', sa.String(64), nullable=False),
            sa.Column('spec', sa.String(255), nullable=False),
            sa.Column('price', sa.Numeric(10, 2), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.ForeignKeyConstraint(['order_id'], ['oms_orders.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
    op.create_index('ix_oms_order_items_order_id', 'oms_order_items', ['order_id'])

    # ── oms_order_operate_logs ──
    if not _table_exists("oms_order_operate_logs"):
        op.create_table(
            'oms_order_operate_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('operate_man', sa.String(100), nullable=False),
            sa.Column('order_status_before', sa.Integer(), nullable=True),
            sa.Column('order_status_after', sa.Integer(), nullable=False),
            sa.Column('note', sa.String(500), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
    op.create_index('ix_oms_order_logs_order_id', 'oms_order_operate_logs', ['order_id'])


def downgrade() -> None:
    op.drop_index('ix_oms_order_logs_order_id', table_name='oms_order_operate_logs')
    op.drop_table('oms_order_operate_logs')
    op.drop_index('ix_oms_order_items_order_id', table_name='oms_order_items')
    op.drop_table('oms_order_items')
    op.drop_index('ix_oms_orders_sn', table_name='oms_orders')
    op.drop_index('ix_oms_orders_status', table_name='oms_orders')
    op.drop_index('ix_oms_orders_user_id', table_name='oms_orders')
    op.drop_table('oms_orders')
    op.drop_index('ix_oms_cart_items_sku_id', table_name='oms_cart_items')
    op.drop_index('ix_oms_cart_items_product_id', table_name='oms_cart_items')
    op.drop_index('ix_oms_cart_items_user_id', table_name='oms_cart_items')
    op.drop_table('oms_cart_items')
