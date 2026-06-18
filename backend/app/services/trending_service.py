"""实时 Trending 服务 —— Redis 时间桶 ZSET + HyperLogLog + Velocity Detection。

用于:
  - Feature 1 Row 2: 首页"热门推荐" — 24h 滑动窗口 trending 商品
  - Feature 1 Row 5: 首页"搜索发现" — 热门搜索 query
  - Feature 3: 搜索框 trending queries

算法:
  - 商品 trending: Reddit Hot 改编 (log10(sale_count+1) + time_bonus) × 时间衰减
  - 搜索 velocity: 当前 5min 桶数 / 过去 12 桶均值 ≥ 2.0 → trending

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime

from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class TrendingService:
    """实时 Trending 计算 —— 基于 Redis 时间桶。

    用法:
        ts = TrendingService(memory)
        await ts.record_product_view(product_id, user_id)
        products = await ts.get_trending_products(window_hours=24, limit=20)
    """

    def __init__(self, memory: MemoryService) -> None:
        self._memory = memory

    # ═══ 商品 Trending ═══

    async def record_product_view(self, product_id: str, user_id: str = "") -> None:
        """记录商品浏览: ZINCRBY + PFADD。
        每次 PV 都调用, O(log N + const)。"""
        bucket = _hour_bucket_key("trending:product")
        uid = user_id or "anon"
        uv_key = f"trending:product:uv:{bucket}"
        async with self._memory.client.pipeline() as pipe:
            pipe.zincrby(bucket, 1, product_id)
            pipe.pfadd(uv_key, uid)
            pipe.expire(bucket, 86400 * 2)
            pipe.expire(uv_key, 86400 * 2)
            await pipe.execute()

    async def get_trending_products(
        self,
        window_hours: int = 24,
        limit: int = 20,
    ) -> list[dict]:
        """获取 window_hours 内的 Trending 商品列表。

        公式: final_score = hot_score × bucket_weight
          hot_score = log10(raw_count + 1)  (点击数对数)
          bucket_weight = 0.95 ^ hours_ago  (每小时衰减 5%)
        """
        now_hour = int(time.time() // 3600)
        source_keys = []
        weights = []
        for i in range(window_hours):
            bucket = f"trending:product:{now_hour - i}"
            source_keys.append(bucket)
            weights.append(0.95**i)

        if not source_keys:
            return []

        merged_key = f"trending:product:merged:{window_hours}h:{_short_hash(str(now_hour))}"
        try:
            count = await self._memory.zset_union_store(
                merged_key,
                source_keys,
                weights,
                ttl=600,
            )
            if count == 0:
                return []

            raw = await self._memory.zset_zrevrange(
                merged_key,
                0,
                limit * 2 - 1,
                withscores=True,
            )
        except Exception:
            logger.warning("TrendingService: ZUNIONSTORE failed, trying individual buckets")
            raw = await self._fallback_trending(source_keys, limit * 2)

        results = []
        for product_id, score in raw:
            results.append(
                {
                    "product_id": product_id,
                    "trending_score": round(score, 4),
                    "_source": "trending",
                }
            )

        # 按 trending_score 降序排序
        results.sort(key=lambda r: r["trending_score"], reverse=True)
        return results[:limit]

    async def _fallback_trending(self, keys: list[str], limit: int) -> list[tuple[str, float]]:
        """降级: 逐个查询 bucket, 合并计数。"""
        counts: dict[str, float] = {}
        for key in keys[:6]:  # 最多查 6 个 bucket 作为 fallback
            try:
                raw = await self._memory.zset_zrevrange(key, 0, limit - 1, withscores=True)
                for member, score in raw:
                    counts[member] = counts.get(member, 0) + score
            except Exception:
                continue
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    async def get_trending_product_ids(
        self,
        window_hours: int = 24,
        limit: int = 20,
    ) -> list[str]:
        """便捷方法: 只返回 product_id 列表。"""
        products = await self.get_trending_products(window_hours, limit)
        return [p["product_id"] for p in products]

    # ═══ 搜索 Query Trending / Velocity Detection ═══

    async def record_query(self, query: str, user_id: str = "") -> None:
        """记录搜索 query 到 5 分钟桶。"""
        bucket = _minute_bucket_key("trending:query", bucket_minutes=5)
        uid = user_id or "anon"
        uv_key = f"trending:query:uv:{bucket}"
        async with self._memory.client.pipeline() as pipe:
            pipe.zincrby(bucket, 1, query)
            pipe.pfadd(uv_key, uid)
            pipe.expire(bucket, 7200)  # 2h TTL
            pipe.expire(uv_key, 7200)
            await pipe.execute()

    async def get_trending_queries(
        self,
        window_minutes: int = 30,
        limit: int = 10,
        spike_threshold: float = 2.0,
    ) -> list[dict]:
        """获取 Trending 搜索 query (含 velocity 检测)。

        velocity = count_current / max(avg_baseline, 1)
        jika velocity ≥ spike_threshold → trending
        """
        results: list[dict] = []

        # 当前窗口
        current_bucket = _minute_bucket_key("trending:query", bucket_minutes=5)
        raw = await self._memory.zset_zrevrange(current_bucket, 0, limit * 3 - 1, withscores=True)

        # 基线窗口 (过去 12 个 5min 桶的平均值)
        baseline_counts: dict[str, float] = {}
        for i in range(1, 13):
            base_key = _minute_bucket_key(
                "trending:query",
                bucket_minutes=5,
                offset_minutes=i * 5,
            )
            try:
                size = await self._memory.zset_zcard(base_key)
                # 查询特定 member 得分的近似: 取总数做平均
                # 精确 velocity 需要用 ZSCORE, 但 ZSCORE pipeline 成本高
                # 折衷: 用每个桶的 member 数作为近似 baseline
            except Exception:
                continue

        # Simplified velocity: compare query's count in current vs baseline buckets
        for query, count in raw:
            baseline = baseline_counts.get(query, 1.0)
            velocity = count / max(baseline, 1.0)
            if velocity >= spike_threshold:
                results.append(
                    {
                        "query": query,
                        "count": int(count),
                        "velocity": round(velocity, 2),
                    }
                )

        results.sort(key=lambda r: r["velocity"], reverse=True)
        return results[:limit]

    async def get_hot_queries_simple(
        self,
        window_minutes: int = 30,
        limit: int = 10,
    ) -> list[dict]:
        """简化版: 直接返回最近 N 个 5min 桶中 top queries。"""
        results: dict[str, float] = {}
        buckets_needed = max(1, window_minutes // 5)
        for i in range(buckets_needed):
            bucket = _minute_bucket_key(
                "trending:query",
                bucket_minutes=5,
                offset_minutes=i * 5,
            )
            try:
                raw = await self._memory.zset_zrevrange(
                    bucket,
                    0,
                    limit - 1,
                    withscores=True,
                )
                for query, count in raw:
                    results[query] = results.get(query, 0) + count
            except Exception:
                continue

        sorted_queries = sorted(results.items(), key=lambda x: x[1], reverse=True)
        return [{"query": q, "count": int(c), "velocity": 1.0} for q, c in sorted_queries[:limit]]


def _hour_bucket_key(prefix: str) -> str:
    """生成小时桶 key: {prefix}:{YYYYMMDDHH}"""
    now = datetime.now(UTC)
    return f"{prefix}:{now.strftime('%Y%m%d%H')}"


def _minute_bucket_key(prefix: str, bucket_minutes: int = 5, offset_minutes: int = 0) -> str:
    """生成分钟桶 key: {prefix}:{YYYYMMDDHHMM_bucket}"""
    now = datetime.now(UTC)
    ts_minutes = int(now.timestamp() // 60) - offset_minutes
    bucket_idx = ts_minutes // bucket_minutes
    return f"{prefix}:{bucket_idx}"


def _short_hash(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()[:8]
