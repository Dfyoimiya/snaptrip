"""init —— 初始化数据库架构

创建所有表、索引和 vector 扩展。

Revision ID: 8da6e575b9c0
Revises:
Create Date: 2026-05-17 11:45:03.719291
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import NullType

revision: str = "8da6e575b9c0"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")

    # ===== users =====
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(128), nullable=False),
        sa.Column("oauth_provider", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ===== user_profiles =====
    op.create_table(
        "user_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nickname", sa.String(64), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("preferences", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("travel_style", sa.String(32), nullable=True),
        sa.Column("home_address", postgresql.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(
        "ALTER TABLE user_profiles ADD COLUMN preference_embedding vector(1536);"
    )

    # ===== plans =====
    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("date_range", postgresql.DATERANGE(), nullable=False),
        sa.Column(
            "group_type",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'solo'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_plans_user_id", "plans", ["user_id"])
    op.create_index("ix_plans_status", "plans", ["status"])
    op.create_index("ix_plans_date_range", "plans", ["date_range"])
    op.create_index("ix_plans_user_id_status", "plans", ["user_id", "status"])
    op.create_foreign_key(
        "fk_plans_user_id_users",
        "plans",
        "users",
        ["user_id"],
        ["id"],
    )

    # ===== plan_slots =====
    op.create_table(
        "plan_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("poi_id", sa.String(128), nullable=False),
        sa.Column("time_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("time_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "slot_status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'tentative'"),
        ),
        sa.Column("booking_ref", sa.String(128), nullable=True),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False, server_default=sa.text("15")),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_plan_slots_plan_id", "plan_slots", ["plan_id"])
    op.create_index("ix_plan_slots_poi_id", "plan_slots", ["poi_id"])
    op.create_index("ix_plan_slots_plan_id_time_start", "plan_slots", ["plan_id", "time_start"])
    op.create_foreign_key(
        "fk_plan_slots_plan_id_plans",
        "plan_slots",
        "plans",
        ["plan_id"],
        ["id"],
    )

    # ===== checkpoints =====
    op.create_table(
        "checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("slots_snapshot", postgresql.JSON(), nullable=False),
        sa.Column("consensus_status", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_checkpoints_plan_id", "checkpoints", ["plan_id"])
    op.create_foreign_key(
        "fk_checkpoints_plan_id_plans",
        "checkpoints",
        "plans",
        ["plan_id"],
        ["id"],
    )

    # ===== plan_adjustments =====
    op.create_table(
        "plan_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_reason", sa.String(255), nullable=False),
        sa.Column("original_slots", postgresql.JSON(), nullable=False),
        sa.Column("adjusted_slots", postgresql.JSON(), nullable=False),
        sa.Column(
            "user_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_foreign_key(
        "fk_plan_adjustments_plan_id_plans",
        "plan_adjustments",
        "plans",
        ["plan_id"],
        ["id"],
    )

    # ===== pois =====
    op.create_table(
        "pois",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("tags", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("avg_rating", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("metadata", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "group_suitability",
            postgresql.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_pois_category", "pois", ["category"])
    op.create_index("ix_pois_lat_lng", "pois", ["lat", "lng"])
    op.execute("ALTER TABLE pois ADD COLUMN embedding vector(1536);")
    op.execute(
        "CREATE INDEX ix_pois_embedding_hnsw ON pois "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )

    # ===== llm_usage_logs =====
    op.create_table(
        "llm_usage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ===== refresh_tokens =====
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_foreign_key(
        "fk_refresh_tokens_user_id_users",
        "refresh_tokens",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("llm_usage_logs")
    op.execute("DROP INDEX IF EXISTS ix_pois_embedding_hnsw;")
    op.drop_table("pois")
    op.drop_table("plan_adjustments")
    op.drop_table("checkpoints")
    op.drop_table("plan_slots")
    op.drop_table("plans")
    op.drop_table("user_profiles")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector;")
