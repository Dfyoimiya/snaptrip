"""deduplicate product categories and add sibling-name uniqueness

Revision ID: q5f6g7h8i9j0
Revises: p4e5f6g7h8i9
Create Date: 2026-06-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "q5f6g7h8i9j0"
down_revision: str | None = "p4e5f6g7h8i9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 每轮合并当前同父级、同名称的重复分类。先迁移商品和子分类引用，
    # 再删除旧分类；父级合并后产生的新一轮子级重复会在下一轮处理。
    op.execute(
        """
        DO $$
        DECLARE
            duplicate_count integer;
        BEGIN
            LOOP
                CREATE TEMP TABLE category_merge_map ON COMMIT DROP AS
                WITH ranked AS (
                    SELECT
                        id AS old_id,
                        first_value(id) OVER (
                            PARTITION BY parent_id, name
                            ORDER BY created_at DESC NULLS LAST, id DESC
                        ) AS keep_id,
                        row_number() OVER (
                            PARTITION BY parent_id, name
                            ORDER BY created_at DESC NULLS LAST, id DESC
                        ) AS row_number
                    FROM pms_categories
                )
                SELECT old_id, keep_id
                FROM ranked
                WHERE row_number > 1;

                SELECT count(*) INTO duplicate_count FROM category_merge_map;
                EXIT WHEN duplicate_count = 0;

                UPDATE pms_products AS product
                SET category_id = merge.keep_id
                FROM category_merge_map AS merge
                WHERE product.category_id = merge.old_id;

                UPDATE pms_categories AS child
                SET parent_id = merge.keep_id
                FROM category_merge_map AS merge
                WHERE child.parent_id = merge.old_id;

                DELETE FROM pms_categories AS category
                USING category_merge_map AS merge
                WHERE category.id = merge.old_id;

                DROP TABLE category_merge_map;
            END LOOP;
        END
        $$;
        """
    )

    op.create_index(
        "uq_pms_categories_root_name",
        "pms_categories",
        ["name"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "uq_pms_categories_parent_name",
        "pms_categories",
        ["parent_id", "name"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_pms_categories_parent_name", table_name="pms_categories")
    op.drop_index("uq_pms_categories_root_name", table_name="pms_categories")
