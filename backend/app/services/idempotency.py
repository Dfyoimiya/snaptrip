"""Idempotency Service —— 基于 Redis SET NX 的幂等性保证。

核心策略:
  - L2 物理操作 (physical_impact=True): Redis 不可用 → fail-fast, 拒绝服务
  - L0/L1 读操作: Redis 不可用 → allow + warning, 允许降级

幂等 Key 格式: idempotent:{plan_id}:{tool_name}:{poi_id}:{slot_index}

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.schemas.tool_provider import ToolProviderConfig

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# types
# ------------------------------------------------------------------


class IdempotencyUnavailableError(Exception):
    """幂等服务不可用 —— 物理操作拒绝服务（不静默降级）。"""

    def __init__(self, retry_after_s: int = 5) -> None:
        self.retry_after_s = retry_after_s
        super().__init__(f"幂等服务不可用，物理操作暂停服务，请在 {retry_after_s}s 后重试")


@dataclass
class IdempotencyDecision:
    """幂等检查结果"""

    allow: bool
    is_duplicate: bool = False
    cached_result: dict | None = None


# ------------------------------------------------------------------
# service
# ------------------------------------------------------------------


class IdempotencyService:
    """基于 Redis SET NX + TTL 的幂等性服务。

    用法:
      service = IdempotencyService(redis_client)
      try:
          decision = await service.acquire(key, tool_config)
      except IdempotencyUnavailableError:
          # 物理操作拒绝服务
          return error_response

      if decision.is_duplicate:
          return cached_response  # 重复请求，返回缓存结果

      result = await do_physical_op()
      await service.mark_completed(key, result)
    """

    def __init__(self, redis_client, default_ttl: int = 3600) -> None:
        self._redis = redis_client
        self._default_ttl = default_ttl

    async def acquire(self, key: str, tool_config: ToolProviderConfig | None = None) -> IdempotencyDecision:
        """获取幂等锁。

        Args:
            key: 幂等 Key
            tool_config: 工具配置（用于判断物理影响 + per-tool TTL）

        Returns:
            IdempotencyDecision

        Raises:
            IdempotencyUnavailable: L2 物理操作 + Redis 不可用
        """
        ttl = tool_config.idempotency_ttl_sec if tool_config else self._default_ttl
        physical_impact = tool_config.physical_impact if tool_config else False

        try:
            acquired = await self._redis.set(key, "1", nx=True, ex=ttl)
        except Exception as e:
            if physical_impact:
                # ★ 物理操作: 宁可拒绝服务，也不重复预订
                logger.critical("idempotency_redis_unavailable key=%s physical_impact=True", key)
                raise IdempotencyUnavailableError(retry_after_s=5) from e

            # 纯读操作: 允许降级
            logger.warning("idempotency_degraded_readonly key=%s error=%s", key, e)
            return IdempotencyDecision(allow=True)

        if acquired:
            return IdempotencyDecision(allow=True)

        # 重复请求 → 尝试返回缓存结果
        try:
            cached_raw = await self._redis.get(key)
            if cached_raw:
                cached = json.loads(cached_raw)
                return IdempotencyDecision(allow=False, is_duplicate=True, cached_result=cached)
        except (json.JSONDecodeError, Exception):
            pass

        return IdempotencyDecision(allow=False, is_duplicate=True)

    async def mark_completed(self, key: str, result: dict, ttl: int | None = None) -> None:
        """标记完成并缓存结果。

        后续重复请求将返回此缓存结果。
        """
        try:
            await self._redis.set(key, json.dumps(result), ex=ttl or self._default_ttl)
        except Exception as e:
            logger.warning("idempotency_mark_failed key=%s error=%s", key, e)

    async def release(self, key: str) -> None:
        """释放幂等锁（Saga 补偿后调用）。

        释放后允许该幂等键被重新使用。
        """
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.warning("idempotency_release_failed key=%s error=%s", key, e)
