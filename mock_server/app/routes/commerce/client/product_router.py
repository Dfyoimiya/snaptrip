"""Mock Server — C端 商品路由."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode

router = APIRouter(prefix="/products")
DATA = Path(__file__).parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("/{product_id}")
async def get_product(product_id: str):
    products = _load("seed_products.json")
    p = next((p for p in products if p["id"] == product_id), None)
    if not p:
        return Result(code=ErrorCode.PROD_NOT_FOUND, message="商品不存在")

    reviews = [r for r in _load("seed_reviews.json") if r.get("product_id") == product_id]
    p["reviews"] = reviews[:5]
    p["reviews_count"] = len(reviews)
    p["review_avg"] = round(sum(r["rating"] for r in reviews) / max(1, len(reviews)), 1) if reviews else 0
    return Result(data=p)


@router.get("/{product_id}/reviews")
async def get_reviews(
    product_id: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    all_reviews = [r for r in _load("seed_reviews.json") if r.get("product_id") == product_id]
    total = len(all_reviews)
    start = (page - 1) * size
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": all_reviews[start:start + size]})


@router.get("/{product_id}/reviews/stats")
async def get_review_stats(product_id: str):
    reviews = [r for r in _load("seed_reviews.json") if r.get("product_id") == product_id]
    if not reviews:
        return Result(data={"avg_rating": 0, "total_count": 0, "distribution": {}})
    avg = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
    dist = {}
    for r in reviews:
        k = str(r["rating"])
        dist[k] = dist.get(k, 0) + 1
    return Result(data={"avg_rating": avg, "total_count": len(reviews), "distribution": dist})
