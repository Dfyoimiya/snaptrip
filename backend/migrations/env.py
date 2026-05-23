"""Alembic 迁移环境配置。

从 app.core.config.settings 读取数据库 URL，自动导入所有模型
以支持 --autogenerate 检测 schema 变更。

Author: SnapTrip Team
Date: 2026-05-22
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from snaptrip_shared.core.config import settings

# ── Alembic Config ──
config = context.config
config.set_main_option("sqlalchemy.url", settings.effective_database_url.replace("+asyncpg", "+psycopg2"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── 导入所有模型以支持 autogenerate ──
from marketplace.app.models.base import Base  # noqa: E402
from agent_worker.app.agent.models.checkpoint import Checkpoint  # noqa: E402, F401
from agent_worker.app.agent.models.llm_usage_log import LLMUsageLog  # noqa: E402, F401
from marketplace.app.models.plan import Plan  # noqa: E402, F401
from marketplace.app.models.plan_adjustment import PlanAdjustment  # noqa: E402, F401
from agent_worker.app.agent.models.plan_run import PlanRun  # noqa: E402, F401
from agent_worker.app.agent.models.plan_run_event import PlanRunEvent  # noqa: E402, F401
from marketplace.app.models.plan_slot import PlanSlot  # noqa: E402, F401
from marketplace.app.models.poi import POI  # noqa: E402, F401
from marketplace.app.models.refresh_token import RefreshToken  # noqa: E402, F401
from agent_worker.app.agent.models.runtime_checkpoint import RuntimeCheckpoint  # noqa: E402, F401
from marketplace.app.models.user_profile import UserProfile  # noqa: E402, F401
from marketplace.app.models.users import User  # noqa: E402, F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
