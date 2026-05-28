"""add created_at to cart_items and favorites

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-26 16:00:00.000000

Bugfix — 补全 OmsCartItem 和 UmsMemberFavorite 的 created_at 字段
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'g7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('oms_cart_items',
                  sa.Column('created_at', sa.DateTime(timezone=True),
                            server_default=sa.text('now()'), nullable=False))
    op.add_column('ums_member_favorites',
                  sa.Column('created_at', sa.DateTime(timezone=True),
                            server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    op.drop_column('ums_member_favorites', 'created_at')
    op.drop_column('oms_cart_items', 'created_at')
