"""Feature Store — Redis-backed user behaviour tracking.

Stores user behaviour events (views, clicks, purchases) in Redis Sorted Sets
with sliding-window aggregation for real-time feature computation.

Adapted from refer/multi-agent-ecommerce-system/python/services/feature_store.py
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FeatureStore:
    """Redis-backed real-time feature store for user behaviour and profiles.

    Features:
      - Append-only behaviour events (Sorted Set, score = timestamp)
      - Sliding-window queries (1h, 24h, 7d)
      - RFM scoring (Recency, Frequency, Monetary)
      - Offline/online tag merging
    """

    def __init__(self, redis_client: Any = None, ttl: int = 86400):
        self.redis = redis_client
        self.ttl = ttl

    # ── Behaviour tracking ────────────────────────────────────────────────────

    async def record_behaviour(
        self,
        user_id: str,
        behaviour_type: str,
        item_id: str,
        metadata: dict | None = None,
    ):
        """Append a behaviour event to user's sorted set."""
        if not self.redis:
            return
        key = f"sg:behavior:{user_id}:{behaviour_type}"
        payload = json.dumps({
            "item_id": item_id,
            "ts": time.time(),
            **(metadata or {}),
        })
        await self.redis.zadd(key, {payload: time.time()})
        await self.redis.expire(key, self.ttl)

    async def get_recent_behaviours(
        self,
        user_id: str,
        behaviour_type: str,
        window_seconds: int = 3600,
    ) -> list[dict]:
        """Retrieve behaviours within a sliding time window."""
        if not self.redis:
            return []
        key = f"sg:behavior:{user_id}:{behaviour_type}"
        cutoff = time.time() - window_seconds
        raw_items = await self.redis.zrangebyscore(key, cutoff, "+inf")
        return [json.loads(item) for item in raw_items]

    # ── Feature aggregation ───────────────────────────────────────────────────

    async def get_user_features(self, user_id: str) -> dict[str, Any]:
        """Build aggregated feature vector from recent behaviours."""
        views_1h = await self.get_recent_behaviours(user_id, "view", 3600)
        views_24h = await self.get_recent_behaviours(user_id, "view", 86400)
        clicks_1h = await self.get_recent_behaviours(user_id, "click", 3600)
        purchases_7d = await self.get_recent_behaviours(user_id, "purchase", 604800)

        recent_view_items = [v.get("item_id", "") for v in views_24h[-20:]]
        recent_purchase_items = [p.get("item_id", "") for p in purchases_7d[-10:]]

        rfm = await self._compute_rfm(purchases_7d)

        # Merge offline tags
        offline_tags = {}
        if self.redis:
            profile_key = f"sg:profile:{user_id}"
            raw = await self.redis.get(profile_key)
            if raw:
                offline_tags = json.loads(raw)

        return {
            "user_id": user_id,
            "view_count_1h": len(views_1h),
            "view_count_24h": len(views_24h),
            "click_count_1h": len(clicks_1h),
            "purchase_count_7d": len(purchases_7d),
            "recent_views": recent_view_items,
            "recent_purchases": recent_purchase_items,
            "rfm": rfm,
            "offline_tags": offline_tags,
        }

    async def _compute_rfm(self, purchases: list[dict]) -> dict[str, float]:
        """Recency / Frequency / Monetary scoring (normalised 0-1)."""
        if not purchases:
            return {"recency": 0.0, "frequency": 0.0, "monetary": 0.0}

        now = time.time()
        latest_ts = max(p.get("ts", 0) for p in purchases)
        days_since = (now - latest_ts) / 86400

        recency = max(0.0, 1.0 - days_since / 30.0)
        frequency = min(1.0, len(purchases) / 10.0)
        avg_amount = sum(p.get("amount", 100) for p in purchases) / max(len(purchases), 1)
        monetary = min(1.0, avg_amount / 1000.0)

        return {
            "recency": round(recency, 3),
            "frequency": round(frequency, 3),
            "monetary": round(monetary, 3),
        }

    # ── Offline tag merge ─────────────────────────────────────────────────────

    async def merge_offline_tags(self, user_id: str, tags: dict[str, Any]):
        """Write offline (batch-computed) tags for the profile agent to read."""
        if not self.redis:
            return
        key = f"sg:profile:{user_id}"
        await self.redis.set(key, json.dumps(tags), ex=self.ttl)
