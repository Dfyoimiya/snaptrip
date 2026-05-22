"""Redis-backed event bus for cross-process SSE streaming.

Agent Worker 进程中替代 in-memory RuntimeEventStore：
    1. 持久化到 plan_run_events 表（SQL）
    2. PUBLISH 到 Redis Pub/Sub 频道

Gateway 通过 SUBSCRIBE 频道接收实时事件。

使用 ConnectionPool（而非直接 client）避免跨 asyncio.run() 的 event loop 绑定问题。

Author: SnapTrip Team
Date: 2026-05-22
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis

from agent_worker.app.agent.ports.events import EventSinkPort
from agent_worker.app.agent.ports.repositories import RuntimeEventRepositoryPort
from agent_worker.app.agent.schemas.events import RuntimeEvent

logger = logging.getLogger(__name__)


class RedisEventBus(EventSinkPort):
    """跨进程事件总线：Redis PUBLISH + SQL 持久化。

    接受 ConnectionPool 而非 Redis client ——
    emit() 在 asyncio.run() 内调用，lazy 创建 client 确保复用同一 event loop。

    Redis 失败不阻塞图执行 —— 降级为纯 SQL 模式。
    """

    def __init__(
        self,
        *,
        pool: aioredis.ConnectionPool,
        repository: RuntimeEventRepositoryPort,
    ) -> None:
        self._pool = pool
        self._repo = repository
        self._redis: aioredis.Redis | None = None

    def _get_redis(self) -> aioredis.Redis:
        """lazy 创建 Redis client（绑定当前 event loop）。"""
        if self._redis is None:
            self._redis = aioredis.Redis(connection_pool=self._pool)
        return self._redis

    async def emit(self, event: RuntimeEvent) -> None:
        """持久化到 SQL 并 PUBLISH 到 Redis。

        Redis 异常不传播 —— 事件丢失只意味着 SSE 实时推送中断，
        但 DB 记录仍可用于后续查询。
        """
        # persist first — durability over real-time
        await self._repo.append(event)

        channel = f"plan:{event.plan_id}:events"
        try:
            redis_client = self._get_redis()
            await redis_client.publish(channel, event.model_dump_json())
        except Exception:
            logger.warning(
                "redis_publish_failed channel=%s event_id=%s",
                channel,
                event.event_id,
                exc_info=True,
            )
