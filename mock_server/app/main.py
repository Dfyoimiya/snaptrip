"""Mock Server — FastAPI 入口。

Two channel architecture:
  - Commerce channel: /api/client/v1/*  &  /api/admin/v1/*
    Response format: {code, message, data}  (contracts.schemas.common.Result)
  - Tool channel: /mock/tools/*
    Response format: {status, data, error_code, error_message, latency_ms}  (ToolResult)

Start: uvicorn app.main:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.fault import fault_injection_middleware
from app.routes.commerce.client import router as client_router
from app.routes.commerce.admin import router as admin_router
from app.routes.tools import router as tools_router

app = FastAPI(
    title="SnapTrip Mock Server",
    description="美团商城Mock服务 —— 商业频道 + 工具频道",
    version="0.3.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fault injection (5% 503, 10% delay) — applied globally
app.middleware("http")(fault_injection_middleware)

# Register channels
app.include_router(client_router)   # /api/client/v1/*
app.include_router(admin_router)    # /api/admin/v1/*
app.include_router(tools_router)    # /mock/tools/*


@app.get("/health")
async def health():
    return {"status": "ok"}
