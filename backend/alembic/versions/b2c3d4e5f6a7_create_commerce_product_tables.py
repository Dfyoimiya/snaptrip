"""create commerce product tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-26 11:00:00.000000

Phase 2 — 创建商品域6张表 + seed 示例数据
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(name: str) -> bool:
    """Check if a table exists in the current database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ── pms_categories ──
    if not _table_exists("pms_categories"):
        op.create_table(
            "pms_categories",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("nav_status", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("show_status", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("icon", sa.String(255), nullable=True),
            sa.Column("keywords", sa.String(255), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["parent_id"], ["pms_categories.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_pms_categories_parent_id", "pms_categories", ["parent_id"])

    # ── pms_brands ──
    if not _table_exists("pms_brands"):
        op.create_table(
            "pms_brands",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("first_letter", sa.String(8), nullable=True),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("factory_status", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("show_status", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("logo", sa.String(255), nullable=True),
            sa.Column("big_pic", sa.String(255), nullable=True),
            sa.Column("brand_story", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── pms_products ──
    if not _table_exists("pms_products"):
        op.create_table(
            "pms_products",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("sub_title", sa.String(255), nullable=True),
            sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("product_sn", sa.String(64), nullable=True),
            sa.Column("price", sa.Numeric(10, 2), nullable=False),
            sa.Column("original_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("promotion_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("promotion_start_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("promotion_end_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("promotion_per_limit", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("promotion_type", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sale_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("pics", sa.String(1000), nullable=True),
            sa.Column("album_pics", sa.String(1000), nullable=True),
            sa.Column("default_pic", sa.String(255), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("keywords", sa.String(255), nullable=True),
            sa.Column("unit", sa.String(16), nullable=True),
            sa.Column("weight", sa.Float(), nullable=True),
            sa.Column("publish_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("new_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("recommend_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("preview_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verify_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("service_ids", sa.String(255), nullable=True),
            sa.Column("feight_template_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("product_sn", name="uq_products_sn"),
        )
    op.create_index("ix_pms_products_brand_id", "pms_products", ["brand_id"])
    op.create_index("ix_pms_products_category_id", "pms_products", ["category_id"])
    op.create_index("ix_pms_products_is_deleted", "pms_products", ["is_deleted"])

    # ── pms_skus ──
    if not _table_exists("pms_skus"):
        op.create_table(
            "pms_skus",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("sku_code", sa.String(64), nullable=False),
            sa.Column("spec", sa.String(255), nullable=False),
            sa.Column("price", sa.Numeric(10, 2), nullable=False),
            sa.Column("promotion_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("low_stock", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lock_stock", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("pic", sa.String(255), nullable=True),
            sa.Column("sale_count", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_pms_skus_product_id", "pms_skus", ["product_id"])

    # ── pms_product_attributes ──
    if not _table_exists("pms_product_attributes"):
        op.create_table(
            "pms_product_attributes",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("attr_type", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("input_type", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("input_list", sa.String(255), nullable=True),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("filter_type", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("search_type", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("related_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hand_add_status", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_pms_product_attrs_category_id", "pms_product_attributes", ["category_id"])

    # ── pms_product_attribute_values ──
    if not _table_exists("pms_product_attribute_values"):
        op.create_table(
            "pms_product_attribute_values",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("attribute_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("value", sa.String(255), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index("ix_pms_attr_values_product_id", "pms_product_attribute_values", ["product_id"])
    op.create_index("ix_pms_attr_values_attribute_id", "pms_product_attribute_values", ["attribute_id"])


def downgrade() -> None:
    op.drop_index("ix_pms_attr_values_attribute_id", table_name="pms_product_attribute_values")
    op.drop_index("ix_pms_attr_values_product_id", table_name="pms_product_attribute_values")
    op.drop_table("pms_product_attribute_values")
    op.drop_index("ix_pms_product_attrs_category_id", table_name="pms_product_attributes")
    op.drop_table("pms_product_attributes")
    op.drop_index("ix_pms_skus_product_id", table_name="pms_skus")
    op.drop_table("pms_skus")
    op.drop_index("ix_pms_products_is_deleted", table_name="pms_products")
    op.drop_index("ix_pms_products_category_id", table_name="pms_products")
    op.drop_index("ix_pms_products_brand_id", table_name="pms_products")
    op.drop_table("pms_products")
    op.drop_table("pms_brands")
    op.drop_index("ix_pms_categories_parent_id", table_name="pms_categories")
    op.drop_table("pms_categories")
