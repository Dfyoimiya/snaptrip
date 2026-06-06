"""Mock Server — C端 搜索路由."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, Query, Request

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode

from app import state
from app.middleware import get_user_from_request

router = APIRouter(prefix="/search")
DATA = Path(__file__).parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("")
async def search(
    q: str = Query(min_length=1, max_length=100),
    type: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    if not q:
        return Result(code=ErrorCode.SRCH_KEYWORD_EMPTY, message="搜索关键词为空")

    kw = q.lower()
    results = []
    if not type or type == "merchant":
        for m in _load("seed_merchants.json"):
            if kw in m["name"].lower() or any(kw in t.lower() for t in m.get("tags", [])):
                results.append({"id": m["id"], "type": "merchant", "name": m["name"], "image": m.get("logo"),
                                "rating": m.get("rating"), "tags": m.get("tags", []), "price": None})
    if not type or type == "product":
        for p in _load("seed_products.json"):
            if kw in p["name"].lower():
                results.append({"id": p["id"], "type": "product", "name": p["name"], "image": p.get("image"),
                                "rating": None, "tags": [], "price": p.get("price")})

    total = len(results)
    start = (page - 1) * size
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": results[start:start + size]})


@router.get("/hot")
async def hot_searches():
    items = _load("seed_hot_searches.json")
    return Result(data=items)


@router.get("/suggestions")
async def suggestions(q: str = Query(min_length=1)):
    kw = q.lower()
    result = []
    for m in _load("seed_merchants.json"):
        if kw in m["name"].lower():
            result.append({"keyword": m["name"], "type": "merchant", "count": m.get("sales", 0)})
    for p in _load("seed_products.json"):
        if kw in p["name"].lower():
            result.append({"keyword": p["name"], "type": "product", "count": p.get("sales", 0)})
    return Result(data=result[:10])


@router.get("/history")
async def search_history(request: Request):
    uid = get_user_from_request(request)
    items = state._search_history.get(uid, []) if uid else []
    return Result(data=items)


@router.delete("/history")
async def clear_history(request: Request):
    uid = get_user_from_request(request)
    if uid:
        state._search_history[uid] = []
    return Result(data=None)
