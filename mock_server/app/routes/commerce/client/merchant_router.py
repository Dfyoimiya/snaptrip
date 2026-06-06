"""Mock Server — C端 商家路由."""

from __future__ import annotations

import json
import math
from pathlib import Path

from fastapi import APIRouter, Query

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode

router = APIRouter(prefix="/merchants")
DATA = Path(__file__).parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _haversine(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("")
async def list_merchants(
    lat: float = Query(default=None),
    lng: float = Query(default=None),
    category_id: str = Query(default=None),
    sort_field: str = Query(default="distance"),
    sort_order: str = Query(default="asc"),
    keyword: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    merchants = _load("seed_merchants.json")

    # Filter
    if category_id:
        merchants = [m for m in merchants if m.get("category_id") == category_id]
    if keyword:
        kw = keyword.lower()
        merchants = [m for m in merchants if kw in m["name"].lower() or any(kw in t.lower() for t in m.get("tags", []))]

    # Distance
    for m in merchants:
        if lat and lng:
            m["distance_km"] = round(_haversine(lat, lng, m["lat"], m["lng"]), 1)
        else:
            m["distance_km"] = None

    # Sort
    if sort_field == "rating":
        merchants.sort(key=lambda m: m.get("rating", 0), reverse=sort_order == "desc")
    elif sort_field == "sales":
        merchants.sort(key=lambda m: m.get("sales", 0), reverse=sort_order == "desc")
    else:  # distance
        merchants.sort(key=lambda m: m.get("distance_km") or 999, reverse=False)

    total = len(merchants)
    start = (page - 1) * size
    page_data = merchants[start:start + size]
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": page_data})


@router.get("/{merchant_id}")
async def get_merchant(merchant_id: str):
    merchants = _load("seed_merchants.json")
    m = next((m for m in merchants if m["id"] == merchant_id), None)
    if not m:
        return Result(code=ErrorCode.MERCH_NOT_FOUND, message="商家不存在")

    products = [p for p in _load("seed_products.json") if p.get("merchant_id") == merchant_id and p.get("status") == "ON_SHELF"]
    categories = _load("seed_categories.json")
    return Result(data={**m, "products": products, "categories": categories})
