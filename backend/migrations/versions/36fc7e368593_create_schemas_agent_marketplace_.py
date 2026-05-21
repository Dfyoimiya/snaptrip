"""create schemas agent marketplace langgraph

Revision ID: 36fc7e368593
Revises: 
Create Date: 2026-05-22 00:52:58.009470

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '36fc7e368593'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 agent / marketplace / langgraph 三个 schema。

    Schema 治理（Phase 4）:
      - agent:       plan_runs, plan_run_events, llm_usage_logs, runtime_checkpoints
      - marketplace: users, user_profiles, plans, plan_slots, plan_adjustments, pois, refresh_tokens
      - langgraph:   checkpoints

    注意: 此迁移仅创建 schema，不移动表。
    表迁移在后续迁移中通过 ALTER TABLE ... SET SCHEMA 完成。
    """
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")
    op.execute("CREATE SCHEMA IF NOT EXISTS marketplace")
    op.execute("CREATE SCHEMA IF NOT EXISTS langgraph")


def downgrade() -> None:
    """回滚：删除三个 schema（仅在无表时安全）。"""
    op.execute("DROP SCHEMA IF EXISTS langgraph CASCADE")
    op.execute("DROP SCHEMA IF EXISTS marketplace CASCADE")
    op.execute("DROP SCHEMA IF EXISTS agent CASCADE")
