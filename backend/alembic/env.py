"""Alembic 异步迁移环境配置。

支持 asyncpg + SQLAlchemy 2.0 异步引擎。
迁移脚本通过 run_sync 桥接同步执行。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from snaptrip_shared.core.config import settings
from marketplace.app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本而不连接数据库。"""
    context.configure(
        url=settings.effective_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """在同步连接上执行迁移。"""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """在线模式：使用异步引擎 + run_sync 桥接。"""
    connectable = create_async_engine(
        settings.effective_database_url,
        echo=settings.APP_DEBUG,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式入口：包装异步函数。"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
