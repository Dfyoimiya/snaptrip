"""Mock Server — B端 数据统计."""

from __future__ import annotations

import json
import random
from pathlib import Path

from fastapi import APIRouter, Query

from contracts.schemas.common import Result

router = APIRouter(prefix="/statistics")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


_days = [f"2024-06-{i:02d}" for i in range(1, 31)]


@router.get("/revenue")
async def revenue_stats(start_date: str = Query(default="2024-06-01"), end_date: str = Query(default="2024-06-30")):
    daily = [{"date": d, "revenue": random.randint(20000, 120000), "order_count": random.randint(10, 100)} for d in _days]
    total = sum(d["revenue"] for d in daily)
    return Result(data={"total_revenue": total, "avg_daily_revenue": round(total / len(daily), 2), "daily_breakdown": daily})


@router.get("/orders")
async def order_stats(start_date: str = Query(default="2024-06-01"), end_date: str = Query(default="2024-06-30")):
    daily = [{"date": d, "total": random.randint(20, 120), "completed": random.randint(15, 100), "cancelled": random.randint(0, 10)} for d in _days]
    total_orders = sum(d["total"] for d in daily)
    completed = sum(d["completed"] for d in daily)
    cancelled = sum(d["cancelled"] for d in daily)
    return Result(data={
        "total_orders": total_orders, "completed_orders": completed, "cancelled_orders": cancelled,
        "completion_rate": round(completed / max(1, total_orders) * 100, 1),
        "status_breakdown": {"PENDING": random.randint(0, 10), "PAID": random.randint(0, 10),
                             "CONFIRMED": random.randint(0, 10), "DELIVERING": random.randint(0, 10),
                             "COMPLETED": completed, "CANCELLED": cancelled},
        "daily_breakdown": daily,
    })


@router.get("/users")
async def user_stats(start_date: str = Query(default="2024-06-01"), end_date: str = Query(default="2024-06-30")):
    daily = [{"date": d, "new_users": random.randint(5, 50), "active_users": random.randint(100, 500)} for d in _days]
    return Result(data={"total_users": random.randint(5000, 20000), "new_users": sum(d["new_users"] for d in daily),
                        "active_users": sum(d["active_users"] for d in daily), "daily_breakdown": daily})


@router.get("/ranking")
async def product_ranking(limit: int = Query(default=10, ge=1, le=50)):
    products = _load("seed_products.json")
    top = sorted(products, key=lambda p: p.get("sales", 0), reverse=True)[:limit]
    ranking = [{"product_id": p["id"], "product_name": p["name"], "sales": p.get("sales", 0),
                "revenue": p.get("price", 0) * p.get("sales", 0), "rank": i + 1} for i, p in enumerate(top)]
    return Result(data=ranking)
