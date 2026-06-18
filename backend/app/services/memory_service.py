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
            raise RuntimeError("MemoryService not started. Call await service.start() first.")
        return self._client

    # ===== 会话状态 =====

    async def set_session_state(self, session_id: str, state: str, ttl: int = 3600) -> None:
        key = f"session:{session_id}:state"
        await self.client.set(key, state, ex=ttl)

    async def get_session_state(self, session_id: str) -> str | None:
        key = f"session:{session_id}:state"
        return await self.client.get(key)  # type: ignore[no-any-return]

    # ===== 对话历史 =====

    async def push_dialogue(self, session_id: str, role: str, content: str, max_keep: int = 10) -> None:
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

    async def set_hot_pois(self, city: str, category: str, data: list[dict], ttl: int = 3600) -> None:
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
        return bool(count < limit)

    # ===== 事务状态 =====

    async def set_transaction_status(self, txn_id: str, status: str, ttl: int = 3600) -> None:
        key = f"txn:{txn_id}:status"
        await self.client.set(key, status, ex=ttl)

    async def get_transaction_status(self, txn_id: str) -> str | None:
        key = f"txn:{txn_id}:status"
        return await self.client.get(key)  # type: ignore[no-any-return]

    # ===== 行为追踪 (推荐系统特征存储) =====

    async def record_behavior(
        self,
        user_id: str,
        behavior_type: str,
        item_id: str,
        metadata: dict | None = None,
        ttl: int = 86400 * 7,
    ) -> None:
        """记录用户行为到 Redis Sorted Set (滑动窗口)。

        Key: behavior:{user_id}:{behavior_type}
        Score: timestamp (unix ms)
        Member: JSON {item_id, ts, ...metadata}
        """
        key = f"behavior:{user_id}:{behavior_type}"
        entry = json.dumps(
            {
                "item_id": item_id,
                "ts": time.time(),
                **(metadata or {}),
            },
            ensure_ascii=False,
        )
        async with self.client.pipeline() as pipe:
            pipe.zadd(key, {entry: time.time()})
            pipe.expire(key, ttl)
            await pipe.execute()

    async def get_recent_behaviors(
        self,
        user_id: str,
        behavior_type: str,
        window_seconds: int = 3600,
    ) -> list[dict]:
        """获取用户最近的行为 (滑动窗口)。

        返回 window_seconds 内的行为事件列表, 按时间倒序。
        """
        key = f"behavior:{user_id}:{behavior_type}"
        min_score = time.time() - window_seconds
        raw = await self.client.zrangebyscore(key, min_score, "+inf")  # type: ignore[misc]
        return [json.loads(item) for item in raw]

    async def cache_user_profile(
        self,
        user_id: str,
        profile: dict,
        ttl: int = 3600,
    ) -> None:
        """缓存用户画像到 Redis (供快速读取)。"""
        key = f"profile:{user_id}"
        await self.client.set(key, json.dumps(profile, ensure_ascii=False), ex=ttl)

    async def get_cached_profile(self, user_id: str) -> dict | None:
        """获取缓存的用户画像。"""
        key = f"profile:{user_id}"
        raw = await self.client.get(key)
        return json.loads(raw) if raw else None

    # ===== 兼容旧接口 (内存 dict stub 过渡) =====

    async def cache_get(self, key: str) -> Any | None:
        raw = await self.client.get(f"cache:{key}")
        return json.loads(raw) if raw else None

    async def cache_set(self, key: str, value: Any, ttl_s: int = 300) -> None:
        await self.client.set(f"cache:{key}", json.dumps(value, ensure_ascii=False), ex=ttl_s)

    async def save(self, key: str, value: Any) -> None:
        await self.client.set(f"store:{key}", json.dumps(value, ensure_ascii=False))

    async def load(self, key: str) -> Any | None:
        raw = await self.client.get(f"store:{key}")
        return json.loads(raw) if raw else None

    # ===== 实时 Trending / Autocomplete / HyperLogLog (Phase 1 推荐升级) =====

    async def zset_union_store(
        self,
        dest_key: str,
        source_keys: list[str],
        weights: list[float] | None = None,
        ttl: int = 3600,
    ) -> int:
        """ZUNIONSTORE: 合并多个 ZSET 到目标 key。

        redis-py >= 5.0 要求 weights 通过 dict 传递: {key: weight}。
        """
        if weights:
            keys_dict: dict[str, float] = dict(zip(source_keys, weights))
            result: int = await self.client.zunionstore(dest_key, keys_dict)
        else:
            result = await self.client.zunionstore(dest_key, source_keys)
        if ttl > 0:
            await self.client.expire(dest_key, ttl)
        return result

    async def zset_zrevrange(
        self,
        key: str,
        start: int,
        stop: int,
        withscores: bool = False,
    ) -> list:
        """ZREVRANGE: 按 score 倒序获取成员。"""
        return await self.client.zrevrange(key, start, stop, withscores=withscores)  # type: ignore[no-any-return]

    async def zset_zincrby(self, key: str, amount: float, member: str) -> float:
        """ZINCRBY: 增加成员 score。"""
        return await self.client.zincrby(key, amount, member)  # type: ignore[no-any-return]

    async def zset_zcard(self, key: str) -> int:
        """ZCARD: 获取 ZSET 大小。"""
        return await self.client.zcard(key)  # type: ignore[no-any-return]

    async def pfadd(self, key: str, *values: str) -> int:
        """PFADD: HyperLogLog 添加元素。"""
        return await self.client.pfadd(key, *values)  # type: ignore[no-any-return]

    async def pfcount(self, key: str) -> int:
        """PFCOUNT: HyperLogLog 估算基数。"""
        return await self.client.pfcount(key)  # type: ignore[no-any-return]

    async def get_recent_viewed_products(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[str]:
        """获取用户最近浏览的商品 ID 列表（去重，倒序）。"""
        key = f"behavior:{user_id}:view"
        data = await self.client.zrevrange(key, 0, limit * 3 - 1)  # type: ignore[misc]
        seen: set[str] = set()
        product_ids: list[str] = []
        for item_json in data:
            try:
                item = json.loads(item_json)
                pid = item.get("item_id", "")
                if pid and pid not in seen:
                    seen.add(pid)
                    product_ids.append(pid)
                    if len(product_ids) >= limit:
                        break
            except (json.JSONDecodeError, TypeError):
                continue
        return product_ids

    async def record_search(self, user_id: str, query: str) -> None:
        """记录用户搜索到 ZSET（供搜索历史和自动补全使用）。"""
        ts = time.time()
        key = f"search_history:{user_id}"
        async with self.client.pipeline() as pipe:
            pipe.zadd(key, {query: ts})
            pipe.zremrangebyrank(key, 0, -21)  # keep last 20
            pipe.expire(key, 86400 * 30)
            await pipe.execute()

    async def get_search_history(self, user_id: str, limit: int = 5) -> list[str]:
        """获取用户最近搜索历史。"""
        key = f"search_history:{user_id}"
        return await self.client.zrevrange(key, 0, limit - 1)  # type: ignore[no-any-return]

    # ===== 客服会话记忆 (Phase 3) =====

    async def save_cs_session_summary(
        self,
        session_id: str,
        summary: dict,
        ttl: int = 86400 * 30,
    ) -> None:
        """缓存客服会话摘要到 Redis + 追加到用户历史列表。

        summary 包含: user_id, intent, summary_text, resolution_status,
                      satisfaction_score, ticket_id, order_id,
                      conversation_turns, tools_called, key_entities, emotion_trajectory
        """
        summary_key = f"cs_session:{session_id}:summary"
        await self.client.set(summary_key, json.dumps(summary, ensure_ascii=False), ex=ttl)

        user_id = summary.get("user_id", "")
        if user_id:
            history_key = f"cs_history:{user_id}"
            async with self.client.pipeline() as pipe:
                pipe.zadd(history_key, {session_id: time.time()})
                pipe.zremrangebyrank(history_key, 0, -51)  # keep last 50
                pipe.expire(history_key, ttl)
                await pipe.execute()

    async def get_cs_session_summary(self, session_id: str) -> dict | None:
        """获取指定客服会话的摘要缓存。"""
        key = f"cs_session:{session_id}:summary"
        raw = await self.client.get(key)
        return json.loads(raw) if raw else None

    async def get_user_cs_history(
        self,
        user_id: str,
        limit: int = 5,
    ) -> list[dict]:
        """获取用户最近的客服会话摘要列表（倒序）。"""
        history_key = f"cs_history:{user_id}"
        session_ids = await self.client.zrevrange(history_key, 0, limit - 1)  # type: ignore[misc]
        summaries: list[dict] = []
        for sid in session_ids:
            summary = await self.get_cs_session_summary(sid)
            if summary:
                summaries.append(summary)
        return summaries

    async def set_cs_session_emotion(
        self,
        session_id: str,
        emotion: str,
        ttl: int = 3600,
    ) -> None:
        """记录当前会话的用户情绪状态。"""
        key = f"cs_session:{session_id}:emotion"
        await self.client.set(key, emotion, ex=ttl)

    async def get_cs_session_emotion(self, session_id: str) -> str:
        """获取当前会话的用户情绪状态。"""
        key = f"cs_session:{session_id}:emotion"
        raw = await self.client.get(key)
        return raw if raw else "neutral"  # type: ignore[no-any-return]
