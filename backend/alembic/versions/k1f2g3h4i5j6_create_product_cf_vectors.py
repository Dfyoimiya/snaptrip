"""create pms_product_cf_vectors table for ALS collaborative filtering

Revision ID: k1f2g3h4i5j6
Revises: j0e1f2a3b4c5
Create Date: 2026-06-16

This migration:
  1. Creates pms_product_cf_vectors table (product_id UNIQUE, cf_vector(64), model_version)
  2. Adds IVFFlat index for ANN similarity search on cf_vector
  3. Adds updated_at column for tracking vector freshness
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k1f2g3h4i5j6"
down_revision: str | None = "j0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 确保 pgvector 扩展已启用
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "pms_product_cf_vectors",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("product_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cf_vector", Vector(64), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 唯一索引: 一个商品只有一个 CF 向量
    op.create_index("ix_pms_product_cf_vectors_product_id", "pms_product_cf_vectors", ["product_id"], unique=True)

    # 外键: 级联删除
    op.create_foreign_key(
        "fk_pms_product_cf_vectors_product_id",
        "pms_product_cf_vectors",
        "pms_products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # IVFFlat 索引用于近似最近邻搜索
    # 注意: IVFFlat 需要在表有一定数据量后创建才有效, 此处先创建占位
    # 实际使用时通过 _ensure_cf_index 按需创建
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cf_vector_ivfflat
        ON pms_product_cf_vectors
        USING ivfflat (cf_vector vector_cosine_ops)
        WITH (lists = 10)
    """)


def downgrade() -> None:
    op.drop_index("idx_cf_vector_ivfflat", table_name="pms_product_cf_vectors", if_exists=True)
    op.drop_constraint("fk_pms_product_cf_vectors_product_id", "pms_product_cf_vectors", type_="foreignkey")
    op.drop_index("ix_pms_product_cf_vectors_product_id", table_name="pms_product_cf_vectors")
    op.drop_table("pms_product_cf_vectors")
