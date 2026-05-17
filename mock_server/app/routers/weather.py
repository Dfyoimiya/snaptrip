"""天气查询路由。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import random
import time

from fastapi import APIRouter, Query

from app.schemas import ToolResult

router = APIRouter(prefix="/weather", tags=["weather"])

CONDITIONS = ["晴", "多云", "阴", "小雨", "中雨", "阵雨"]


@router.get("")
async def get_weather(
    city: str = Query("北京"),
    date: str = Query(""),
):
    t0 = time.perf_counter()
    condition = random.choice(CONDITIONS)
    temp = random.randint(15, 35)

    return ToolResult(
        status="success",
        data={
            "city": city,
            "date": date or "today",
            "temp_high": temp + random.randint(1, 4),
            "temp_low": temp - random.randint(5, 10),
            "condition": condition,
            "humidity": random.randint(30, 90),
            "wind_level": random.randint(1, 5),
            "aqi": random.randint(30, 150),
            "suitable_for_outdoor": condition not in ("中雨", "阵雨"),
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()
