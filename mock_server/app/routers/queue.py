"""排队查询路由。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import random
import time

from fastapi import APIRouter, Query

from app.schemas import ToolResult

router = APIRouter(prefix="/poi", tags=["queue"])


@router.get("/queue")
async def check_queue(
    poi_id: str = Query(...),
    date: str = Query(""),
    party_size: int = Query(2),
):
    t0 = time.perf_counter()
    wait_minutes = random.randint(0, 30)
    can_take_number = random.choice([True, False])
    available_slots = []
    if can_take_number:
        available_slots = [
            f"{h:02d}:{m:02d}"
            for h, m in [(11, 30), (12, 0), (12, 30), (13, 0), (18, 0), (18, 30), (19, 0)]
            if random.random() > 0.5
        ]

    return ToolResult(
        status="success",
        data={
            "poi_id": poi_id,
            "wait_minutes": wait_minutes,
            "can_take_number_online": can_take_number,
            "available_slots": available_slots,
            "queue_length": random.randint(0, 20),
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()
