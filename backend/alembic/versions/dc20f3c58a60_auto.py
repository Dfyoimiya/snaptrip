"""add pms_product_reviews

Revision ID: dc20f3c58a60
Revises: p4e5f6g7h8i9
Create Date: 2026-06-22 20:45:06.625633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc20f3c58a60'
down_revision: Union[str, Sequence[str], None] = 'p4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('pms_product_reviews',
    sa.Column('product_id', sa.UUID(), nullable=False, comment='商品ID'),
    sa.Column('user_id', sa.UUID(), nullable=False, comment='用户ID'),
    sa.Column('order_id', sa.UUID(), nullable=True, comment='关联订单ID (可选)'),
    sa.Column('rating', sa.Integer(), nullable=False, comment='评分: 1~5 星'),
    sa.Column('content', sa.Text(), nullable=True, comment='评价文字内容'),
    sa.Column('images', sa.String(length=1000), nullable=True, comment='评价图片, 逗号分隔URL'),
    sa.Column('is_anonymous', sa.Boolean(), nullable=False, comment='是否匿名评价'),
    sa.Column('status', sa.Integer(), nullable=False, comment='审核状态: 0=待审核 1=通过 2=驳回'),
    sa.Column('reply', sa.Text(), nullable=True, comment='商家回复内容'),
    sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True, comment='商家回复时间'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['pms_products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'product_id', name='uq_user_product_review')
    )
    op.create_index(op.f('ix_pms_product_reviews_is_deleted'), 'pms_product_reviews', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_pms_product_reviews_product_id'), 'pms_product_reviews', ['product_id'], unique=False)
    op.create_index(op.f('ix_pms_product_reviews_user_id'), 'pms_product_reviews', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_pms_product_reviews_user_id'), table_name='pms_product_reviews')
    op.drop_index(op.f('ix_pms_product_reviews_product_id'), table_name='pms_product_reviews')
    op.drop_index(op.f('ix_pms_product_reviews_is_deleted'), table_name='pms_product_reviews')
    op.drop_table('pms_product_reviews')
