"""Redis 连接池管理器。

提供模块级连接池，避免每次 SSE 连接或事件发布新建 TCP 连接。

用法:
    from snaptrip_shared.db.redis import get_redis_client

    client = await get_redis_client()
    await client.publish("channel", "message")

Author: SnapTrip Team
Date: 2026-05-22
"""

from __future__ import annotations

import redis.asyncio as aioredis

from snaptrip_shared.core.config import settings

_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    """获取或创建模块级 Redis 连接池。"""
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_SIZE,
        )
    return _pool


async def get_redis_client() -> aioredis.Redis:
    """从连接池获取 Redis 客户端。"""
    return aioredis.Redis(connection_pool=get_redis_pool())


async def close_redis_pool() -> None:
    """关闭连接池（在 shutdown 时调用）。"""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
