"""SnapTrip API —— FastAPI 入口（Agent 架构版）。

应用生命周期:
- startup: 初始化 MasterController + MemoryService + MockGateway
- shutdown: 清理 MockGateway 连接

路由注册:
- /api/v1/plan/*  —— 计划创建/查询/SSE流
- /api/v1/auth/*  —— 注册/登录/刷新/登出/个人资料
- /health          —— 健康检查

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.agents.hub import MasterController
from app.api.v1.auth import router as auth_router
from app.api.v1.plan import router as plan_router
from app.api.v1.user import router as user_router
from app.core.response import (
    APIException,
    api_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.services.memory_service import MemoryService
from app.services.mock_gateway import MockAPIGateway


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.hub = MasterController()
    app.state.memory = MemoryService()
    app.state.mock_gateway = MockAPIGateway()
    await app.state.memory.start()
    await app.state.mock_gateway.start()
    yield
    await app.state.mock_gateway.stop()
    await app.state.memory.stop()


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

app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.get("/health")
async def health():
    return {"status": "ok"}
