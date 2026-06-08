"""SnapTrip API —— FastAPI 入口（Agent 架构版）。

应用生命周期:
- startup: 初始化 MemoryService + RedisEventBus + AgentRuntime
- shutdown: 清理 Redis 连接池

路由注册:
- /api/v1/plan/*  —— 计划创建/查询/SSE流
- /api/v1/auth/*  —— 注册/登录/刷新/登出/个人资料
- /health          —— 健康检查

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from agent.adapters.marketplace import MarketplaceClient
from agent.adapters.persistence.runtime_event import SQLRuntimeEventRepository
from agent.events.redis_bus import RedisEventBus
from agent.graph import build_graph
from app.services.memory_service import MemoryService
from agent.runtime import AgentRuntime
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from snaptrip_shared.core.config import settings
from snaptrip_shared.core.exception_handlers import (
    adapter_exception_handler,
    authentication_handler,
    circuit_breaker_handler,
    not_found_handler,
    permission_denied_handler,
    rate_limit_handler,
    snap_trip_exception_handler,
    validation_handler,
)
from snaptrip_shared.core.exceptions import (
    AdapterError,
    AmapRateLimitError,
    AuthenticationError,
    CircuitBreakerOpenError,
    PermissionDeniedError,
    ResourceNotFoundError,
    SnapTripException,
    ValidationError,
)
from snaptrip_shared.core.response import (
    APIServiceError,
    api_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from snaptrip_shared.db.redis import close_redis_pool, get_redis_pool
from starlette.exceptions import HTTPException as StarletteHTTPException

from marketplace.app.api.v1.auth import router as auth_router
from marketplace.app.api.v1.plan import router as plan_router
from marketplace.app.api.v1.user import router as user_router
from marketplace.app.api.v1.admin_agent import router as admin_agent_router

# ── 电商路由 (Commerce) ──
from app.api.admin import admin_router
from app.api.portal import portal_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.memory = MemoryService()
    app.state.redis_pool = get_redis_pool()
    app.state.marketplace_client = MarketplaceClient(mode=settings.MARKETPLACE_MODE)

    event_bus = RedisEventBus(
        pool=app.state.redis_pool,
        repository=SQLRuntimeEventRepository(),
    )
    runtime = AgentRuntime(event_bus=event_bus)
    app.state.plan_graph = await build_graph(runtime=runtime)

    yield
    await app.state.memory.stop()
    await close_redis_pool()


app = FastAPI(
    title="SnapTrip",
    description="本地生活智能规划与执行系统",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plan_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_agent_router)

# ── 电商路由 —— Admin + Portal 统一前缀 /api/v1 ──
app.include_router(admin_router, prefix="/api/v1")
app.include_router(portal_router, prefix="/api/v1")

app.add_exception_handler(APIServiceError, api_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

# 统一异常体系 —— SOCID Consistent Exception
app.add_exception_handler(AdapterError, adapter_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(AmapRateLimitError, rate_limit_handler)  # type: ignore[arg-type]
app.add_exception_handler(AuthenticationError, authentication_handler)  # type: ignore[arg-type]
app.add_exception_handler(CircuitBreakerOpenError, circuit_breaker_handler)  # type: ignore[arg-type]
app.add_exception_handler(PermissionDeniedError, permission_denied_handler)  # type: ignore[arg-type]
app.add_exception_handler(ResourceNotFoundError, not_found_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValidationError, validation_handler)  # type: ignore[arg-type]
app.add_exception_handler(SnapTripException, snap_trip_exception_handler)  # type: ignore[arg-type]


@app.get("/health")
async def health():
    return {"status": "ok"}
