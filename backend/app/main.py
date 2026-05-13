"""SnapTrip API —— FastAPI 入口（Agent 架构版）。

应用生命周期:
- startup: 初始化 MasterController + MemoryService + MockGateway
- shutdown: 清理 MockGateway 连接

路由注册:
- /api/v1/plan/*  —— 计划创建/查询/SSE流
- /health          —— 健康检查

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.hub import MasterController
from app.api.v1.plan import router as plan_router
from app.services.memory_service import MemoryService
from app.services.mock_gateway import MockAPIGateway


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.hub = MasterController()
    app.state.memory = MemoryService()
    app.state.mock_gateway = MockAPIGateway()
    await app.state.mock_gateway.start()
    yield
    await app.state.mock_gateway.stop()


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


@app.get("/health")
async def health():
    return {"status": "ok"}
