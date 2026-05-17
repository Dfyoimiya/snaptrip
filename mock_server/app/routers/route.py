"""路线规划路由。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import math
import random
import time

from fastapi import APIRouter, Query

from app.schemas import ToolResult

router = APIRouter(prefix="/route", tags=["route"])


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


SPEED_MAP: dict[str, float] = {
    "walk": 5.0,
    "drive": 40.0,
    "transit": 25.0,
}


@router.get("")
async def get_route(
    from_lat: float = Query(...),
    from_lng: float = Query(...),
    to_lat: float = Query(...),
    to_lng: float = Query(...),
    mode: str = Query("walk"),
):
    t0 = time.perf_counter()
    if mode not in SPEED_MAP:
        mode = "walk"

    dist_km = _haversine(from_lat, from_lng, to_lat, to_lng)
    speed = SPEED_MAP[mode]
    duration_min = int((dist_km / speed) * 60 + random.uniform(-5, 5))
    duration_min = max(1, duration_min)

    steps_count = min(max(1, int(dist_km * 2)), 20)
    polyline = [[from_lat + i * (to_lat - from_lat) / steps_count,
                 from_lng + i * (to_lng - from_lng) / steps_count]
                for i in range(steps_count + 1)]

    return ToolResult(
        status="success",
        data={
            "distance_km": round(dist_km, 2),
            "duration_min": duration_min,
            "mode": mode,
            "polyline": polyline,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()
