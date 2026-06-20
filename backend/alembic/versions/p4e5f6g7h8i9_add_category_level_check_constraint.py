"""add CHECK constraint to pms_categories.level

Revision ID: p4e5f6g7h8i9
Revises: 6570aeae929c
Create Date: 2026-06-20

This migration adds a database-level CHECK constraint to enforce
level >= 0 AND level <= 2 on the pms_categories table, ensuring
no category can exceed the maximum depth of 2 (3 levels: 0/1/2).

The constraint is named ck_pms_categories_level_range to match
the SQLAlchemy model definition.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "p4e5f6g7h8i9"
down_revision: str | None = "6570aeae929c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        constraint_name="ck_pms_categories_level_range",
        table_name="pms_categories",
        condition="level >= 0 AND level <= 2",
    )


def downgrade() -> None:
    op.drop_constraint(
        constraint_name="ck_pms_categories_level_range",
        table_name="pms_categories",
        type_="check",
    )
