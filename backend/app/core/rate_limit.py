"""限流中间件 —— 基于 Redis 滑动窗口。

- IP 限流: 100 req/min（路由白名单除外）
- 用户限流: 300 req/min（已认证用户）

白名单路由（跳过限流和认证）:
    /api/v1/auth/*, /health, /docs, /openapi.json, /redoc

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.services.memory_service import MemoryService

WHITELIST_PREFIXES = (
    "/api/v1/auth",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def _is_whitelisted(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in WHITELIST_PREFIXES)


def get_memory(request: Request) -> MemoryService:
    return request.app.state.memory  # type: ignore[no-any-return]


async def rate_limit_ip(
    request: Request,
    memory: MemoryService = Depends(get_memory),
) -> None:
    path = request.url.path
    if _is_whitelisted(path):
        return
    client_ip = request.client.host if request.client else "unknown"
    key = f"ip:{client_ip}"
    allowed = await memory.sliding_window_check(key, limit=settings.RATE_LIMIT_IP_PER_MIN, window=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )


async def rate_limit_user(
    request: Request,
    user_id: str | None = None,
    memory: MemoryService = Depends(get_memory),
) -> None:
    if user_id is None:
        return
    path = request.url.path
    if _is_whitelisted(path):
        return
    key = f"user:{user_id}"
    allowed = await memory.sliding_window_check(key, limit=settings.RATE_LIMIT_USER_PER_MIN, window=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )
