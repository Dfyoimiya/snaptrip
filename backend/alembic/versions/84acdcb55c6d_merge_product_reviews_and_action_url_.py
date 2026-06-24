"""merge product_reviews and action_url branches

Revision ID: 84acdcb55c6d
Revises: r6g7h8i9j0k1, dc20f3c58a60
Create Date: 2026-06-23 16:18:33.344418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84acdcb55c6d'
down_revision: Union[str, Sequence[str], None] = ('r6g7h8i9j0k1', 'dc20f3c58a60')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
