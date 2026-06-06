"""Mock Server — C端 首页路由 (banners, categories, recommend)."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from fastapi import APIRouter, Query

from contracts.schemas.common import Result

router = APIRouter(prefix="/home")
DATA = Path(__file__).parent.parent.parent.parent.parent / "data"


def _load_json(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _haversine(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("/banners")
async def get_banners():
    banners = [b for b in _load_json("seed_banners.json") if b.get("status") == "ACTIVE"]
    return Result(data=banners)


@router.get("/categories")
async def get_categories():
    cats = _load_json("seed_categories.json")
    top = [c for c in cats if not c.get("parent_id")]
    return Result(data=top)


@router.get("/recommend")
async def get_recommend(
    lat: float = Query(default=39.9),
    lng: float = Query(default=116.4),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    merchants = _load_json("seed_merchants.json")
    for m in merchants:
        m["distance_km"] = round(_haversine(lat, lng, m["lat"], m["lng"]), 1)
    # Weight: closer + higher rating
    merchants.sort(key=lambda m: m.get("distance_km", 99) - m.get("rating", 0) * 0.5)
    total = len(merchants)
    start = (page - 1) * size
    page_data = merchants[start:start + size]
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": page_data})
