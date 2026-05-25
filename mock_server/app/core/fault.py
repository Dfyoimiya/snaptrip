"""Mock Server — fault injection middleware (5% 503, 10% delay)."""

from __future__ import annotations

import asyncio
import random

from fastapi import Request
from fastapi.responses import JSONResponse


async def fault_injection_middleware(request: Request, call_next):
    """Inject random faults for resilience testing.

    - 5% chance: return 503 SERVICE_UNAVAILABLE
    - 10% chance: inject 1-3 second delay
    - Otherwise: pass through to next handler
    """
    roll = random.random()

    if roll < 0.05:
        return JSONResponse(
            status_code=503,
            content={
                "status": "failure",
                "data": None,
                "error_code": "SERVICE_UNAVAILABLE",
                "error_message": "Mock service temporarily unavailable",
                "latency_ms": 0,
            },
        )

    if roll < 0.15:
        delay = random.uniform(1.0, 3.0)
        await asyncio.sleep(delay)

    response = await call_next(request)
    return response
