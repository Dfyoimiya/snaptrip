"""Memory Service — Redis/PostgreSQL 统一访问层 (Stub)"""

from __future__ import annotations

from typing import Any, Dict, Optional


class MemoryService:
    """记忆服务：封装 Redis 缓存 + PostgreSQL 持久化"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._store: Dict[str, Any] = {}

    async def start(self):
        pass

    async def stop(self):
        pass

    async def cache_get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    async def cache_set(self, key: str, value: Any, ttl_s: int = 300):
        self._cache[key] = value

    async def save(self, key: str, value: Any):
        self._store[key] = value

    async def load(self, key: str) -> Optional[Any]:
        return self._store.get(key)
