"""自动补全服务 —— Redis ZSET 前缀索引。

用于:
  - Feature 3a: 搜索框输入自动补全
  - Feature 3b: 热门搜索 query velocity

Redis key 设计:
  - autocomplete:{prefix_char}  → ZSET of (query, freq)
    例如: query "跑步鞋" →
      ZADD autocomplete:跑 1 "跑步鞋"
      ZADD autocomplete:跑步 1 "跑步鞋"
  - search_history:{user_id}   → ZSET of (query, timestamp)

离线批量构建: 扫描 ums_member_search_logs 统计 query 频次
在线增量更新: 每次搜索时 ZINCRBY

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import logging

from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# 自动补全 ZSET TTL (30天)
AUTOCOMPLETE_TTL = 86400 * 30


class AutocompleteService:
    """Redis 前缀自动补全索引。

    用法:
        svc = AutocompleteService(memory)
        await svc.build_index(search_logs)  # 离线批量构建
        await svc.increment("跑步鞋")        # 在线增量
        suggestions = await svc.suggest("跑", limit=8)
    """

    def __init__(self, memory: MemoryService) -> None:
        self._memory = memory

    async def suggest(self, prefix: str, limit: int = 8) -> list[dict]:
        """前缀搜索建议。

        策略:
          - prefix length ≥ 2: ZREVRANGE autocomplete:{prefix[0]} + autocomplete:{prefix[:2]}
            精确前缀匹配优先, 首字匹配兜底
          - prefix length = 1: ZREVRANGE autocomplete:{prefix}
        """
        suggestions: list[tuple[str, float]] = []
        seen: set[str] = set()

        if len(prefix) >= 2:
            # 精确前缀匹配 (如 "跑步")
            exact_key = f"autocomplete:{prefix}"
            raw = await self._memory.zset_zrevrange(exact_key, 0, limit - 1, withscores=True)
            for query, score in raw:
                if query not in seen and query.startswith(prefix):
                    suggestions.append((query, score))
                    seen.add(query)
                    if len(suggestions) >= limit:
                        break

            # 首字匹配兜底 (如 "跑")
            if len(suggestions) < limit:
                char_key = f"autocomplete:{prefix[0]}"
                raw2 = await self._memory.zset_zrevrange(
                    char_key,
                    0,
                    limit * 2 - 1,
                    withscores=True,
                )
                for query, score in raw2:
                    if query not in seen and query.startswith(prefix):
                        suggestions.append((query, score))
                        seen.add(query)
                        if len(suggestions) >= limit:
                            break
        else:
            key = f"autocomplete:{prefix}"
            raw = await self._memory.zset_zrevrange(key, 0, limit - 1, withscores=True)
            for query, score in raw:
                if query not in seen and query.startswith(prefix):
                    suggestions.append((query, score))
                    seen.add(query)

        return [{"query": q, "frequency": int(s), "type": "autocomplete"} for q, s in suggestions[:limit]]

    async def increment(self, query: str) -> None:
        """每次搜索时增量更新自动补全索引。

        为 query 的每个前缀 (1~len) 增加 1 分。
        """
        if not query.strip():
            return
        q = query.strip()
        async with self._memory.client.pipeline() as pipe:
            for i in range(1, len(q) + 1):
                key = f"autocomplete:{q[:i]}"
                pipe.zincrby(key, 1, q)
                pipe.expire(key, AUTOCOMPLETE_TTL)
            await pipe.execute()

    async def build_index(self, query_counts: dict[str, int]) -> int:
        """离线批量构建自动补全索引。

        Args:
            query_counts: {query: total_frequency} dict (from search_logs)

        Returns:
            插入的 key 数量
        """
        # 清除旧索引 (按 prefix 逐个)
        all_prefixes: set[str] = set()
        for query in query_counts:
            for i in range(1, len(query) + 1):
                all_prefixes.add(f"autocomplete:{query[:i]}")

        # Pipeline 批量 ZADD
        key_count = 0
        batch: dict[str, dict[str, int]] = {}  # {key: {member: score}}
        for query, freq in query_counts.items():
            if not query.strip():
                continue
            q = query.strip()
            for i in range(1, len(q) + 1):
                key = f"autocomplete:{q[:i]}"
                if key not in batch:
                    batch[key] = {}
                batch[key][q] = max(batch[key].get(q, 0), freq)

        async with self._memory.client.pipeline() as pipe:
            for key, members in batch.items():
                for member, score in members.items():
                    pipe.zadd(key, {member: score})
                pipe.expire(key, AUTOCOMPLETE_TTL)
                key_count += 1
            await pipe.execute()

        logger.info("AutocompleteService: built index with %d prefix keys", key_count)
        return key_count

    async def build_from_search_logs(
        self,
        db_factory,
        top_n: int = 500,
    ) -> int:
        """从数据库 search_logs 构建自动补全索引。

        Args:
            db_factory: SQLAlchemy async session factory
            top_n: 取 top N 个搜索 query
        """
        from sqlalchemy import func, select, text

        from app.models.member.behavior import UmsMemberSearchLog

        async with db_factory() as db:
            stmt = (
                select(
                    UmsMemberSearchLog.keyword,
                    func.count(UmsMemberSearchLog.id).label("cnt"),
                )
                .group_by(UmsMemberSearchLog.keyword)
                .order_by(text("cnt DESC"))
                .limit(top_n)
            )
            result = await db.execute(stmt)
            rows = result.fetchall()

        query_counts = {row[0]: row[1] for row in rows if row[0]}
        return await self.build_index(query_counts)
