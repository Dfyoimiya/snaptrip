"""add phone_number to user

Revision ID: o4d5e6f7g8h9
Revises: n3c4d5e6f7g8
Create Date: 2026-06-18

This migration adds a nullable phone_number column to the users table.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "o4d5e6f7g8h9"
down_revision: str | None = "n3c4d5e6f7g8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone_number", sa.String(20), nullable=True, comment="手机号码"),
    )
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_column("users", "phone_number")
