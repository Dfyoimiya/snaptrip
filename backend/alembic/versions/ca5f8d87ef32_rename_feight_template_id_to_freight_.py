"""rename feight_template_id to freight_template_id

Revision ID: ca5f8d87ef32
Revises: h8c9d0e1f2a3
Create Date: 2026-06-15 15:18:00.057361

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ca5f8d87ef32"
down_revision: Union[str, Sequence[str], None] = "h8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename feight_template_id column to freight_template_id on pms_products."""
    op.alter_column(
        "pms_products",
        "feight_template_id",
        new_column_name="freight_template_id",
    )


def downgrade() -> None:
    """Revert freight_template_id back to feight_template_id."""
    op.alter_column(
        "pms_products",
        "freight_template_id",
        new_column_name="feight_template_id",
    )
