"""alter embedding dimension 1536→384 for sentence-transformers

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
Create Date: 2026-06-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa

revision: str = 'j0e1f2a3b4c5'
down_revision: Union[str, None] = 'i9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE pms_product_embeddings ALTER COLUMN embedding TYPE vector(384)")
    op.execute("UPDATE pms_product_embeddings SET model_name = 'all-MiniLM-L6-v2'")
    op.alter_column('pms_product_embeddings', 'model_name',
                    server_default='all-MiniLM-L6-v2')


def downgrade() -> None:
    op.execute("ALTER TABLE pms_product_embeddings ALTER COLUMN embedding TYPE vector(1536)")
    op.execute("UPDATE pms_product_embeddings SET model_name = 'text-embedding-3-small'")
    op.alter_column('pms_product_embeddings', 'model_name',
                    server_default='text-embedding-3-small')
