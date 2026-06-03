"""SnapTrip API —— FastAPI 入口。

注意：当前运营后端为 backend/marketplace/app/main.py。
本文件为 Phase 2 重构占位，待后续开发。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SnapTrip",
    description="本地生活智能规划与执行系统",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
