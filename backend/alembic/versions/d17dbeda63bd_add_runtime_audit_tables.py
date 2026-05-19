"""add runtime audit tables

创建 plan_runs、plan_run_events、runtime_checkpoints 三张表，
支持运行时事件持久化与审计。

Revision ID: d17dbeda63bd
Revises: 8da6e575b9c0
Create Date: 2026-05-19 10:30:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d17dbeda63bd"
down_revision: Union[str, Sequence[str], None] = "8da6e575b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== plan_runs =====
    op.create_table(
        "plan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("thread_id", sa.String(64), nullable=False),
        sa.Column("graph_version", sa.String(64), nullable=False),
        sa.Column("request_payload", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("final_status", sa.String(32), nullable=False, server_default=sa.text("'created'")),
        sa.Column("seed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("debug", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_plan_runs_run_id", "plan_runs", ["run_id"], unique=True)
    op.create_index("ix_plan_runs_plan_id", "plan_runs", ["plan_id"])
    op.create_index("ix_plan_runs_thread_id", "plan_runs", ["thread_id"])

    # ===== plan_run_events =====
    op.create_table(
        "plan_run_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("node_name", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_json", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_plan_run_events_event_id", "plan_run_events", ["event_id"], unique=True)
    op.create_index("ix_plan_run_events_run_id", "plan_run_events", ["run_id"])
    op.create_index("ix_plan_run_events_plan_id", "plan_run_events", ["plan_id"])
    op.create_index("ix_plan_run_events_node_name", "plan_run_events", ["node_name"])
    op.create_index("ix_plan_run_events_event_type", "plan_run_events", ["event_type"])

    # ===== runtime_checkpoints =====
    op.create_table(
        "runtime_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("state_json", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_runtime_checkpoints_plan_id", "runtime_checkpoints", ["plan_id"])
    op.create_index("ix_runtime_checkpoints_run_id", "runtime_checkpoints", ["run_id"])


def downgrade() -> None:
    op.drop_table("runtime_checkpoints")
    op.drop_table("plan_run_events")
    op.drop_table("plan_runs")
