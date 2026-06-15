"""
基于 Redis 的滑动窗口速率限制器。

用于保护认证端点免受暴力攻击。

Author: SnapTrip Team
Date: 2026-06-14
"""

from __future__ import annotations

import time

from fastapi import HTTPException, Request, status


class RateLimiter:
    """滑动窗口速率限制器（Redis 后端）。"""

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        key_prefix: str = "rate_limit",
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP（支持代理转发）。"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _redis_key(self, ip: str, endpoint: str) -> str:
        return f"{self.key_prefix}:{endpoint}:{ip}"

    async def __call__(self, request: Request) -> None:
        """FastAPI 依赖 —— 检查并递增计数。"""
        from snaptrip_shared.db.redis import get_redis_client

        redis = await get_redis_client()
        ip = self._get_client_ip(request)
        # 从路由中提取端点名（如 "login", "register"）
        endpoint = request.url.path.rstrip("/").rsplit("/", 1)[-1]
        key = self._redis_key(ip, endpoint)
        now = time.time()
        window_start = now - self.window_seconds

        async with redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.window_seconds + 1)
            _, count, *_ = await pipe.execute()

        if count and count > self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试",
            )


# 预设限制器
login_limiter = RateLimiter(
    max_requests=10,
    window_seconds=60,
    key_prefix="rate_limit:login",
)

register_limiter = RateLimiter(
    max_requests=5,
    window_seconds=60,
    key_prefix="rate_limit:register",
)

refresh_limiter = RateLimiter(
    max_requests=30,
    window_seconds=60,
    key_prefix="rate_limit:refresh",
)
