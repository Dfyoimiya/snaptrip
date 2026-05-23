"""POI 搜索路由。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from app.schemas import ToolResult

router = APIRouter(prefix="/poi", tags=["poi"])


def _load_pois() -> list[dict[str, Any]]:
    path = Path(__file__).parent.parent.parent / "data" / "seed_pois.json"
    with open(path) as f:
        return json.load(f)


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


@router.get("/search")
async def search_poi(
    lat: float = Query(39.9),
    lng: float = Query(116.4),
    radius: float = Query(15.0),
    keyword: str = Query(""),
    category: str = Query(""),
    group_type: str = Query(""),
    limit: int = Query(10, le=20),
):
    t0 = time.perf_counter()
    pois = _load_pois()

    result = []
    for p in pois:
        dist = _haversine(lat, lng, p["lat"], p["lng"])
        if dist > radius:
            continue
        if keyword and keyword.lower() not in p["name"].lower() and not any(
            keyword.lower() in t.lower() for t in p["tags"]
        ):
            continue
        if category and p["category"] != category:
            continue
        if group_type:
            suit = p.get("group_suitability", {}).get(group_type, 0.0)
            if suit < 0.6:
                continue
        p_copy = dict(p)
        p_copy["distance_km"] = round(dist, 1)
        result.append(p_copy)

    result.sort(key=lambda x: x["distance_km"])
    result = result[:limit]

    return ToolResult(
        status="success",
        data={"pois": result, "total": len(result)},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()
