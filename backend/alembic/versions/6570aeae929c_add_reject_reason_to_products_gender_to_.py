"""add reject_reason to products, gender to profiles, type to categories

Revision ID: 6570aeae929c
Revises: 3f7dd5da5bff
Create Date: 2026-06-18 12:55:57.879369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6570aeae929c'
down_revision: Union[str, Sequence[str], None] = '3f7dd5da5bff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── pms_products.reject_reason ──
    op.add_column("pms_products", sa.Column("reject_reason", sa.Text(), nullable=True, comment="审核拒绝原因"))

    # ── user_profiles.gender ──
    op.add_column("user_profiles", sa.Column("gender", sa.Integer(), nullable=True, comment="0=未知 1=男 2=女"))

    # ── pms_categories.type ──
    op.add_column("pms_categories", sa.Column("type", sa.String(length=20), nullable=True, comment="分类类型: PRODUCT/COMBO"))


def downgrade() -> None:
    op.drop_column("pms_categories", "type")
    op.drop_column("user_profiles", "gender")
    op.drop_column("pms_products", "reject_reason")
