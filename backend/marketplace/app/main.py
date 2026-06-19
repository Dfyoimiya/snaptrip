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

import logging
import os
from contextlib import asynccontextmanager

from agent.adapters.persistence.runtime_event import SQLRuntimeEventRepository
from agent.events.redis_bus import RedisEventBus
from agent.runtime import AgentRuntime
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from snaptrip_shared.core.config import settings

logger = logging.getLogger(__name__)
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
from snaptrip_shared.db.session import AsyncSessionLocal
from starlette.exceptions import HTTPException as StarletteHTTPException

# ── 电商路由 (Commerce) ──
from app.api.admin import admin_router
from app.api.portal import portal_router
from app.services.ab_test import ABTestEngine
from app.services.autocomplete_service import AutocompleteService
from app.services.collaborative_filtering_service import CollaborativeFilteringService
from app.services.feature_service import FeatureService
from app.services.memory_service import MemoryService
from app.services.trending_service import TrendingService
from app.services.vector_search_service import VectorSearchService
from marketplace.app.api.v1.admin_agent import router as admin_agent_router
from marketplace.app.api.v1.auth import router as auth_router
from marketplace.app.api.v1.plan import router as plan_router
from marketplace.app.api.v1.user import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Memory + Redis ──
    memory = MemoryService()
    await memory.start()
    app.state.memory = memory
    app.state.redis_pool = get_redis_pool()
    event_bus = RedisEventBus(
        pool=app.state.redis_pool,
        repository=SQLRuntimeEventRepository(),
    )
    runtime = AgentRuntime(event_bus=event_bus)

    try:
        from agent.graph import build_graph
        from agent.nodes.recommendation.supervisor import RecommendationSupervisor

        app.state.plan_graph = await build_graph(runtime=runtime)

        # ── 推荐系统 ──
        ab_engine = ABTestEngine()
        feature_svc = FeatureService(db_factory=AsyncSessionLocal, memory=memory)
        trending_svc = TrendingService(memory)
        vector_svc = VectorSearchService(db_factory=AsyncSessionLocal, memory=memory)
        autocomplete_svc = AutocompleteService(memory)
        app.state.recommendation_supervisor = RecommendationSupervisor(
            llm_adapter=runtime.llm_adapter,
            db_factory=AsyncSessionLocal,
            feature_service=feature_svc,
            es_client=None,
            ab_engine=ab_engine,
        )
        app.state.ab_engine = ab_engine
        app.state.feature_service = feature_svc
        app.state.trending_service = trending_svc
        app.state.vector_search_service = vector_svc
        app.state.autocomplete_service = autocomplete_svc
        app.state.cf_service = CollaborativeFilteringService(
            db_factory=AsyncSessionLocal,
            memory=memory,
        )
    except Exception:
        logger.warning(
            "Agent/LLM initialization failed — continuing without agent graph. "
            "Set LITELLM_API_KEY and ensure LiteLLM proxy is reachable.",
            exc_info=True,
        )
        app.state.plan_graph = None

    yield
    await app.state.memory.stop()
    await close_redis_pool()


app = FastAPI(
    title="SnapTrip",
    description="本地生活智能规划与执行系统",
    version="0.2.0",
    lifespan=lifespan,
)


def _get_cors_origins() -> list[str]:
    """Resolve allowed CORS origins from environment, safe by default in production."""
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if cors_origins_env:
        return [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    if settings.APP_ENV in ("development", "test"):
        return ["*"]
    raise ValueError(
        "CORS_ORIGINS environment variable must be set in production mode. "
        "Set it to a comma-separated list of allowed origins, e.g. "
        "CORS_ORIGINS=https://example.com,https://admin.example.com"
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plan_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_agent_router, prefix="/api/v1")

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
