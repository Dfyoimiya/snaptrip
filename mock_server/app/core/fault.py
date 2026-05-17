"""故障注入中间件 —— 模拟真实环境不稳定。

- 5% 概率返回 HTTP 503
- 10% 概率注入 1-3s 延迟

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import asyncio
import random
import time

from fastapi import Request
from fastapi.responses import JSONResponse


async def fault_injection_middleware(request: Request, call_next):
    """全局故障注入中间件"""
    t0 = time.perf_counter()

    # 5% 概率 503
    if random.random() < 0.05:
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

    # 10% 概率注入 1-3s 延迟
    if random.random() < 0.10:
        delay = random.uniform(1.0, 3.0)
        await asyncio.sleep(delay)

    response = await call_next(request)
    return response
