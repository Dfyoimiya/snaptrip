"""故障注入中间件 —— 模拟真实环境不稳定。

通过环境变量控制:
  MOCK_FAULT_RATE  - 503 概率（默认 0.05, CI 设为 0）
  MOCK_DELAY_RATE  - 延迟注入概率（默认 0.10, CI 设为 0）
  /health 路由免除故障注入

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import asyncio
import os
import random
import time

from fastapi import Request
from fastapi.responses import JSONResponse

_FAULT_RATE = float(os.getenv("MOCK_FAULT_RATE", "0.05"))
_DELAY_RATE = float(os.getenv("MOCK_DELAY_RATE", "0.10"))


async def fault_injection_middleware(request: Request, call_next):
    """全局故障注入中间件"""
    if request.url.path == "/health":
        return await call_next(request)

    t0 = time.perf_counter()

    if random.random() < _FAULT_RATE:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return JSONResponse(
            status_code=503,
            content={
                "status": "failure",
                "data": None,
                "error_code": "SERVICE_UNAVAILABLE",
                "error_message": "Mock service temporarily unavailable",
                "latency_ms": latency_ms,
            },
        )

    if random.random() < _DELAY_RATE:
        delay = random.uniform(1.0, 3.0)
        await asyncio.sleep(delay)

    response = await call_next(request)
    return response
