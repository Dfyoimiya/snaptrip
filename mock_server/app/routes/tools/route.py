"""Mock Server — tool routes: route planning, weather, delivery."""

from __future__ import annotations

import math
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.schemas import ToolResult

router = APIRouter()


def _haversine(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("/route")
async def get_route(
    from_lat: float = Query(...),
    from_lng: float = Query(...),
    to_lat: float = Query(...),
    to_lng: float = Query(...),
    mode: str = Query(default="walk"),
):
    t0 = time.perf_counter()
    dist = _haversine(from_lat, from_lng, to_lat, to_lng)
    speeds = {"walk": 5.0, "drive": 40.0, "transit": 25.0}
    speed = speeds.get(mode, 5.0)
    duration = max(1, int(dist / speed * 60) + random.randint(-5, 5))
    steps = max(2, int(dist * 10))
    polyline = [
        [from_lng + (to_lng - from_lng) * i / steps, from_lat + (to_lat - from_lat) * i / steps]
        for i in range(steps + 1)
    ]
    elapsed = int((time.perf_counter() - t0) * 1000)
    return ToolResult(
        status="success",
        data={"distance_km": round(dist, 2), "duration_min": duration, "mode": mode, "polyline": polyline},
        latency_ms=elapsed,
    )


@router.get("/weather")
async def get_weather(city: str = Query(default="北京"), date: str = Query(default="")):
    t0 = time.perf_counter()
    conditions = ["晴", "多云", "阴", "小雨", "中雨", "阵雨"]
    condition = random.choice(conditions)
    temp_high = random.randint(15, 35) + random.randint(1, 4)
    elapsed = int((time.perf_counter() - t0) * 1000)
    return ToolResult(
        status="success",
        data={
            "city": city,
            "date": date or "today",
            "temp_high": temp_high,
            "temp_low": temp_high - random.randint(5, 10),
            "condition": condition,
            "humidity": random.randint(30, 90),
            "wind_level": random.randint(1, 5),
            "aqi": random.randint(30, 150),
            "suitable_for_outdoor": condition not in ("中雨", "阵雨"),
        },
        latency_ms=elapsed,
    )


@router.post("/delivery/schedule")
async def schedule_delivery(body: dict):
    t0 = time.perf_counter()
    try:
        expected = datetime.fromisoformat(body.get("expected_time", ""))
    except (ValueError, TypeError):
        expected = datetime.now(timezone.utc) + timedelta(hours=1)
    estimated = expected + timedelta(minutes=random.randint(0, 15))
    delivery_id = uuid.uuid4().hex[:12]
    elapsed = int((time.perf_counter() - t0) * 1000)
    return ToolResult(
        status="success",
        data={
            "delivery_id": delivery_id,
            "item_type": body.get("item_type", ""),
            "from_poi_id": body.get("from_poi_id", ""),
            "to_poi_id": body.get("to_poi_id", ""),
            "expected_time": expected.isoformat(),
            "estimated_arrival": estimated.isoformat(),
            "fee": random.randint(10, 50),
            "recipient_phone": body.get("recipient_phone", ""),
        },
        latency_ms=elapsed,
    )
