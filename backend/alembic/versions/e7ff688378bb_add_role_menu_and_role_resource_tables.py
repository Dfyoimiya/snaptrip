"""add role_menu and role_resource tables

Revision ID: e7ff688378bb
Revises: ca5f8d87ef32
Create Date: 2026-06-15 15:18:03.792024

This migration creates the menu/resource domain tables plus their RBAC association tables:

  - ums_menus             — Admin navigation menu tree
  - ums_resource_categories — Grouping for backend API resources
  - ums_resources         — Individual backend API resources (with FK to ums_resource_categories)
  - ums_role_menus        — Role-to-menu many-to-many (FK to ums_roles + ums_menus)
  - ums_role_resources    — Role-to-resource many-to-many (FK to ums_roles + ums_resources)

Creation order respects FK dependency: menus/resource_categories first, then
resources (depends on resource_categories), then association tables last.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e7ff688378bb"
down_revision: Union[str, Sequence[str], None] = "ca5f8d87ef32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    """Check if a table exists in the current database."""
    from sqlalchemy import inspect, text

    conn = op.get_bind()
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    """Create menu, resource, and role-association tables (idempotent)."""

    # ── ums_menus ──
    if not _table_exists("ums_menus"):
        op.create_table(
            "ums_menus",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("title", sa.String(64), nullable=False),
            sa.Column("name", sa.String(64), nullable=True),
            sa.Column("icon", sa.String(64), nullable=True),
            sa.Column("sort", sa.Integer(), nullable=False),
            sa.Column("hidden", sa.Integer(), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── ums_resource_categories ──
    if not _table_exists("ums_resource_categories"):
        op.create_table(
            "ums_resource_categories",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("sort", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── ums_resources (FK → ums_resource_categories) ──
    if not _table_exists("ums_resources"):
        op.create_table(
            "ums_resources",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("url", sa.String(128), nullable=True),
            sa.Column("description", sa.String(255), nullable=True),
            sa.ForeignKeyConstraint(
                ["category_id"], ["ums_resource_categories.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── ums_role_menus (FK → ums_roles + ums_menus) ──
    if not _table_exists("ums_role_menus"):
        op.create_table(
            "ums_role_menus",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("menu_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["ums_roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["menu_id"], ["ums_menus.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("role_id", "menu_id", "id"),
            sa.UniqueConstraint("role_id", "menu_id", name="uq_role_menu"),
        )

    # ── ums_role_resources (FK → ums_roles + ums_resources) ──
    if not _table_exists("ums_role_resources"):
        op.create_table(
            "ums_role_resources",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["ums_roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["resource_id"], ["ums_resources.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("role_id", "resource_id", "id"),
            sa.UniqueConstraint("role_id", "resource_id", name="uq_role_resource"),
        )


def downgrade() -> None:
    """Drop association tables first, then dependent tables, then base tables."""
    op.drop_table("ums_role_resources")
    op.drop_table("ums_role_menus")
    op.drop_table("ums_resources")
    op.drop_table("ums_resource_categories")
    op.drop_table("ums_menus")
