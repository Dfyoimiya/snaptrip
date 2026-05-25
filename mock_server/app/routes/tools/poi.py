"""Mock Server — tool routes: POI search (existing logic reconstructed)."""

from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

from fastapi import APIRouter, Query

from app.schemas import ToolResult

router = APIRouter()
SEED_PATH = Path(__file__).parent.parent.parent / "data" / "seed_pois.json"


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load_pois() -> list[dict]:
    if SEED_PATH.exists():
        return json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return []


@router.get("/poi/search")
async def search_poi(
    lat: float = Query(default=39.9),
    lng: float = Query(default=116.4),
    radius: float = Query(default=15.0),
    keyword: str = Query(default=""),
    category: str = Query(default=""),
    group_type: str = Query(default=""),
    limit: int = Query(default=10, le=50),
):
    t0 = time.perf_counter()
    pois = _load_pois()
    results = []

    for poi in pois:
        dist = _haversine(lat, lng, poi["lat"], poi["lng"])
        if dist > radius:
            continue
        if keyword and keyword.lower() not in poi["name"].lower() and not any(
            keyword.lower() in t.lower() for t in poi.get("tags", [])
        ):
            continue
        if category and poi.get("category", "") != category:
            continue
        if group_type:
            gs = poi.get("group_suitability", {})
            if gs.get(group_type, 0) < 0.6:
                continue
        poi["distance_km"] = round(dist, 1)
        results.append(poi)

    results.sort(key=lambda x: x.get("distance_km", 999))
    results = results[:limit]
    elapsed = int((time.perf_counter() - t0) * 1000)

    return ToolResult(status="success", data={"pois": results, "total": len(results)}, latency_ms=elapsed)


@router.get("/poi/queue")
async def check_queue(
    poi_id: str = Query(...),
    date: str = Query(default=""),
    party_size: int = Query(default=2),
):
    t0 = time.perf_counter()
    slots = ["11:30", "12:00", "12:30", "13:00", "18:00", "18:30", "19:00"]
    available = [s for s in slots if random.random() > 0.5]
    elapsed = int((time.perf_counter() - t0) * 1000)

    return ToolResult(
        status="success",
        data={
            "poi_id": poi_id,
            "wait_minutes": random.randint(0, 30),
            "can_take_number_online": random.choice([True, False]),
            "available_slots": available,
            "queue_length": random.randint(0, 20),
        },
        latency_ms=elapsed,
    )


@router.get("/poi/{poi_id}/availability")
async def check_availability(poi_id: str):
    t0 = time.perf_counter()
    elapsed = int((time.perf_counter() - t0) * 1000)
    return ToolResult(
        status="success",
        data={"poi_id": poi_id, "available": random.choice([True, False])},
        latency_ms=elapsed,
    )
