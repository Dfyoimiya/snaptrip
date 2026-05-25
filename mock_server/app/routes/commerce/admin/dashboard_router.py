"""Mock Server — B端 仪表盘."""

from __future__ import annotations

import random

from fastapi import APIRouter

from contracts.schemas.common import Result

router = APIRouter(prefix="/dashboard")


@router.get("")
async def dashboard():
    revenue = random.randint(50000, 200000)
    return Result(data={
        "today_revenue": revenue,
        "today_orders": random.randint(10, 150),
        "today_new_users": random.randint(5, 80),
        "pending_orders": random.randint(0, 30),
        "revenue_trend": [{"date": f"2024-06-{i:02d}", "revenue": random.randint(30000, 150000)} for i in range(1, 31)],
    })
