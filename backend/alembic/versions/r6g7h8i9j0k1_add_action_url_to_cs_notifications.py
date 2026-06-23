"""add action_url to cs_notifications

Revision ID: r6g7h8i9j0k1
Revises: q5f6g7h8i9j0
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "r6g7h8i9j0k1"
down_revision: str | None = "q5f6g7h8i9j0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cs_notifications",
        sa.Column(
            "action_url",
            sa.String(length=512),
            nullable=True,
            comment="B端点击通知后的站内跳转地址",
        ),
    )


def downgrade() -> None:
    op.drop_column("cs_notifications", "action_url")
