"""配送/跑腿路由。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.schemas import ToolResult

router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.post("/schedule")
async def schedule_delivery(body: dict):
    t0 = time.perf_counter()
    delivery_id = str(uuid.uuid4())

    expected_time_str = body.get("expected_time", "")
    try:
        eta = datetime.fromisoformat(expected_time_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        eta = datetime.now(timezone.utc) + timedelta(hours=1)

    offset = random.randint(0, 15)
    estimated_arrival = eta + timedelta(minutes=offset)
    fee = round(random.uniform(10, 50), 2)

    return ToolResult(
        status="success",
        data={
            "delivery_id": delivery_id,
            "item_type": body.get("item_type", ""),
            "from_poi_id": body.get("from_poi_id", ""),
            "to_poi_id": body.get("to_poi_id", ""),
            "expected_time": expected_time_str,
            "estimated_arrival": estimated_arrival.isoformat(),
            "fee": fee,
            "recipient_phone": body.get("recipient_phone", ""),
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()
