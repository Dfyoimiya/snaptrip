"""数据库连接管理 —— asyncpg + SQLAlchemy 2.0 异步会话。

提供:
- async_engine: 全局异步引擎
- AsyncSessionLocal: 异步会话工厂
- get_db: FastAPI 依赖注入，yield AsyncSession

测试环境 (APP_ENV=test) 自动使用 NullPool 避免跨事件循环问题。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from snaptrip_shared.core.config import settings

# Celery worker processes use asyncio.run() per-task, which creates a new event
# loop each time.  The normal connection pool holds connections bound to old
# event loops, causing "Event loop is closed" / "Future attached to different
# loop" errors on cleanup.  NullPool avoids this by not pooling at all — each
# session gets a fresh connection that is closed cleanly.
_celery_worker = (
    len(sys.argv) > 1
    and "worker" in sys.argv
)

_engine_kwargs: dict[str, Any] = {
    "echo": settings.APP_DEBUG,
}
if settings.APP_ENV == "test" or _celery_worker:
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

async_engine = create_async_engine(
    settings.effective_database_url,
    **_engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
