"""Memory Service —— Redis/PostgreSQL 统一访问层 (Stub)。

封装底层存储访问，Agent 不直接操作 Redis/Postgres。

当前实现: 内存 dict 模拟，供开发阶段使用。
远期: Redis 缓存 (会话状态 + POI 检索) + PostgreSQL 持久化 (用户画像 + Checkpoint)

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from typing import Any


class MemoryService:
    """记忆服务：封装 Redis 缓存 + PostgreSQL 持久化"""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._store: dict[str, Any] = {}

    async def start(self) -> None:
        pass

    async def stop(self):
        pass

    async def cache_get(self, key: str) -> Any | None:
        return self._cache.get(key)

    async def cache_set(self, key: str, value: Any, ttl_s: int = 300):
        self._cache[key] = value

    async def save(self, key: str, value: Any):
        self._store[key] = value

    async def load(self, key: str) -> Any | None:
        return self._store.get(key)
