"""Memory Service —— Redis 缓存 + 解耦封装。

提供会话状态、对话历史、热门 POI、滑动窗口限流、事务状态的 Redis 操作接口。
Agent 不直接操作 Redis，全部通过 MemoryService 访问。

使用 redis.asyncio (redis-py >= 5.0)。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from redis.asyncio import Redis
from snaptrip_shared.core.config import settings


class MemoryService:
    """记忆服务：封装 Redis 异步操作"""

    def __init__(self, redis_url: str = "") -> None:
        self._redis_url = redis_url or settings.REDIS_URL
        self._client: Redis | None = None

    # ===== 生命周期 =====

    async def start(self) -> None:
        self._client = Redis.from_url(
            self._redis_url,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=True,
        )
        await self._client.ping()  # type: ignore[misc]

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError(
                "MemoryService not started. Call await service.start() first."
            )
        return self._client

    # ===== 会话状态 =====

    async def set_session_state(
        self, session_id: str, state: str, ttl: int = 3600
    ) -> None:
        key = f"session:{session_id}:state"
        await self.client.set(key, state, ex=ttl)

    async def get_session_state(self, session_id: str) -> str | None:
        key = f"session:{session_id}:state"
        return await self.client.get(key)  # type: ignore[no-any-return]

    # ===== 对话历史 =====

    async def push_dialogue(
        self, session_id: str, role: str, content: str, max_keep: int = 10
    ) -> None:
        key = f"session:{session_id}:dialogue"
        entry = json.dumps({"role": role, "content": content, "ts": time.time()})
        async with self.client.pipeline() as pipe:
            pipe.rpush(key, entry)
            pipe.ltrim(key, -max_keep, -1)
            await pipe.execute()

    async def get_dialogue(self, session_id: str) -> list[dict]:
        key = f"session:{session_id}:dialogue"
        raw = await self.client.lrange(key, 0, -1)  # type: ignore[misc]
        return [json.loads(item) for item in raw]

    # ===== 热门 POI 缓存 =====

    async def set_hot_pois(
        self, city: str, category: str, data: list[dict], ttl: int = 3600
    ) -> None:
        key = f"hot_pois:{city}:{category}"
        await self.client.set(key, json.dumps(data, ensure_ascii=False), ex=ttl)

    async def get_hot_pois(self, city: str, category: str) -> list | None:
        key = f"hot_pois:{city}:{category}"
        raw = await self.client.get(key)
        return json.loads(raw) if raw else None

    # ===== 滑动窗口限流 =====

    async def sliding_window_check(self, key: str, limit: int, window: int) -> bool:
        now_ms = int(time.time() * 1000)
        window_start = now_ms - window * 1000
        redis_key = f"rate_limit:{key}"
        member = f"{now_ms}:{uuid.uuid4().hex[:8]}"
        async with self.client.pipeline() as pipe:
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {member: now_ms})
            pipe.expire(redis_key, window + 1)
            _, count, _, _ = await pipe.execute()
        return count < limit  # type: ignore[no-any-return]

    # ===== 事务状态 =====

    async def set_transaction_status(
        self, txn_id: str, status: str, ttl: int = 3600
    ) -> None:
        key = f"txn:{txn_id}:status"
        await self.client.set(key, status, ex=ttl)

    async def get_transaction_status(self, txn_id: str) -> str | None:
        key = f"txn:{txn_id}:status"
        return await self.client.get(key)  # type: ignore[no-any-return]

    # ===== 兼容旧接口 (内存 dict stub 过渡) =====

    async def cache_get(self, key: str) -> Any | None:
        raw = await self.client.get(f"cache:{key}")
        return json.loads(raw) if raw else None

    async def cache_set(self, key: str, value: Any, ttl_s: int = 300) -> None:
        await self.client.set(
            f"cache:{key}", json.dumps(value, ensure_ascii=False), ex=ttl_s
        )

    async def save(self, key: str, value: Any) -> None:
        await self.client.set(f"store:{key}", json.dumps(value, ensure_ascii=False))

    async def load(self, key: str) -> Any | None:
        raw = await self.client.get(f"store:{key}")
        return json.loads(raw) if raw else None
