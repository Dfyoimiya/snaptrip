"""电影票务路由 —— 影片/影院/场次/选座/下单。

参考猫眼电影 API 设计。

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import json
import math
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from app.schemas import ToolResult, _make_id

router = APIRouter(tags=["movie"])

_seat_locks: dict[str, dict] = {}  # session_id -> {seat_key -> expires_at}
_orders: dict[str, dict] = {}


def _load_movies() -> list[dict[str, Any]]:
    path = Path(__file__).parent.parent.parent / "data" / "seed_movies.json"
    with open(path) as f:
        return json.load(f)


def _load_cinemas() -> list[dict[str, Any]]:
    path = Path(__file__).parent.parent.parent / "data" / "seed_cinemas.json"
    with open(path) as f:
        return json.load(f)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# =============================================================================
# 影片
# =============================================================================


@router.get("/movie/list")
async def list_movies(
    status: str = Query("now_showing", description="now_showing / coming_soon"),
):
    """热映/即将上映影片列表。"""
    t0 = time.perf_counter()
    movies = _load_movies()
    if status == "now_showing":
        movies = [m for m in movies if m["is_now_showing"]]
    else:
        movies = [m for m in movies if not m["is_now_showing"]]

    # 返回简化列表
    result = [{
        "id": m["id"], "title": m["title"], "category": m["category"],
        "duration_min": m["duration_min"], "rating": m["rating"],
        "want_count": m["want_count"], "poster": m.get("poster", ""),
        "release_date": m["release_date"],
    } for m in movies]

    return ToolResult(
        status="success",
        data={"movies": result, "total": len(result)},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/movie/{movie_id}")
async def get_movie_detail(movie_id: str):
    """影片详情。"""
    t0 = time.perf_counter()
    movies = _load_movies()
    for m in movies:
        if m["id"] == movie_id:
            return ToolResult(
                status="success",
                data=m,
                latency_ms=int((time.perf_counter() - t0) * 1000),
            ).model_dump()
    return ToolResult(
        status="failure",
        error_code="MOVIE_NOT_FOUND",
        error_message=f"影片 {movie_id} 不存在",
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


# =============================================================================
# 影院
# =============================================================================


@router.get("/cinema/search")
async def search_cinemas(
    lat: float = Query(39.9),
    lng: float = Query(116.4),
    radius: float = Query(10.0),
    limit: int = Query(20, le=30),
):
    """搜索影院。"""
    t0 = time.perf_counter()
    cinemas = _load_cinemas()

    result = []
    for c in cinemas:
        dist = _haversine(lat, lng, c["lat"], c["lng"])
        if dist > radius:
            continue
        result.append({
            "id": c["id"], "name": c["name"], "city": c["city"],
            "address": c["address"], "distance_km": round(dist, 1),
            "hall_count": c["hall_count"], "tags": c["tags"],
            "avg_rating": c["avg_rating"],
        })

    result.sort(key=lambda x: x["distance_km"])
    result = result[:limit]

    return ToolResult(
        status="success",
        data={"cinemas": result, "total": len(result)},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/cinema/{cinema_id}/sessions")
async def get_cinema_sessions(
    cinema_id: str,
    date: str = Query("", description="日期 YYYY-MM-DD，默认今天"),
    movie_id: str = Query("", description="按影片筛选"),
):
    """某影院某日所有场次。"""
    t0 = time.perf_counter()
    cinemas = _load_cinemas()
    cinema = next((c for c in cinemas if c["id"] == cinema_id), None)
    if cinema is None:
        return ToolResult(
            status="failure",
            error_code="CINEMA_NOT_FOUND",
            error_message=f"影院 {cinema_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    movies = _load_movies()
    showing = [m for m in movies if m["is_now_showing"]]

    if movie_id:
        showing = [m for m in showing if m["id"] == movie_id]

    sessions = _generate_sessions(cinema, showing, date)

    return ToolResult(
        status="success",
        data={
            "cinema_id": cinema_id,
            "cinema_name": cinema["name"],
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "sessions": sessions,
            "total": len(sessions),
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/movie/{movie_id}/sessions")
async def get_movie_sessions(
    movie_id: str,
    lat: float = Query(39.9),
    lng: float = Query(116.4),
    date: str = Query(""),
    radius: float = Query(10.0),
):
    """某影片在某区域的所有场次。"""
    t0 = time.perf_counter()
    movies = _load_movies()
    movie = next((m for m in movies if m["id"] == movie_id), None)
    if movie is None:
        return ToolResult(
            status="failure",
            error_code="MOVIE_NOT_FOUND",
            error_message=f"影片 {movie_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    cinemas = _load_cinemas()
    result = []
    for cinema in cinemas:
        dist = _haversine(lat, lng, cinema["lat"], cinema["lng"])
        if dist > radius:
            continue
        sessions = _generate_sessions(cinema, [movie], date)
        for s in sessions:
            s["cinema_name"] = cinema["name"]
            s["cinema_address"] = cinema["address"]
            s["cinema_distance_km"] = round(dist, 1)
        result.append({
            "cinema_id": cinema["id"],
            "cinema_name": cinema["name"],
            "distance_km": round(dist, 1),
            "sessions": sessions,
        })

    result.sort(key=lambda x: x["distance_km"])

    return ToolResult(
        status="success",
        data={
            "movie_id": movie_id,
            "movie_title": movie["title"],
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "cinemas": result,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


# =============================================================================
# 座位 & 选座
# =============================================================================


@router.get("/session/{session_id}/seats")
async def get_session_seats(session_id: str):
    """场次座位图。"""
    t0 = time.perf_counter()
    seats = _generate_seats(row_count=12, col_count=14)
    _seat_locks.setdefault(session_id, {})

    # 标记已锁座位
    locks = _seat_locks[session_id]
    now = datetime.now(timezone.utc)
    for key, lock in list(locks.items()):
        if now > lock["expires_at"]:
            del locks[key]
        else:
            r, c = key.split("-")
            for seat in seats:
                if seat["row"] == int(r) and seat["col"] == int(c):
                    seat["status"] = "locked"

    return ToolResult(
        status="success",
        data={
            "session_id": session_id,
            "rows": 12,
            "cols": 14,
            "seats": seats,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/movie/order/lock-seats")
async def lock_seats(body: dict):
    """锁座（15 分钟过期）。"""
    t0 = time.perf_counter()
    session_id = body.get("session_id", "")
    seat_keys = body.get("seats", [])  # ["5-12", "5-13"]

    locks = _seat_locks.setdefault(session_id, {})
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=15)

    # 检查冲突
    for key in seat_keys:
        if key in locks:
            lock = locks[key]
            if now < lock["expires_at"]:
                return ToolResult(
                    status="failure",
                    error_code="SEAT_TAKEN",
                    error_message=f"座位 {key} 已被锁定",
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                ).model_dump()

    lock_id = _make_id("lock")
    for key in seat_keys:
        locks[key] = {"lock_id": lock_id, "expires_at": expires_at, "user_id": body.get("user_id", "")}

    return ToolResult(
        status="success",
        data={
            "lock_id": lock_id,
            "session_id": session_id,
            "seats": seat_keys,
            "expires_at": expires_at.isoformat(),
            "expires_in_seconds": 900,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/movie/order/submit")
async def submit_movie_order(body: dict):
    """确认下单（需先锁座）。"""
    t0 = time.perf_counter()
    session_id = body.get("session_id", "")
    lock_id = body.get("lock_id", "")
    seats = body.get("seats", [])

    # 验证锁
    locks = _seat_locks.get(session_id, {})
    for key in seats:
        lock = locks.get(key)
        if lock is None or lock["lock_id"] != lock_id:
            return ToolResult(
                status="failure",
                error_code="SEAT_LOCK_INVALID",
                error_message=f"座位 {key} 锁无效或已过期",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            ).model_dump()
        if datetime.now(timezone.utc) > lock["expires_at"]:
            return ToolResult(
                status="failure",
                error_code="SEAT_LOCK_EXPIRED",
                error_message=f"座位 {key} 锁定已过期",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            ).model_dump()

    # 5% 失败率
    if random.random() < 0.05:
        return ToolResult(
            status="failure",
            error_code="ORDER_FAILED",
            error_message="下单失败，请重试",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    order_id = _make_id("mvo")
    total = round(len(seats) * random.uniform(35, 80), 1)
    order = {
        "order_id": order_id,
        "session_id": session_id,
        "seats": seats,
        "total": total,
        "status": "paid",
        "ticket_code": f"TC{random.randint(10000000, 99999999)}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _orders[order_id] = order

    # 清除锁
    for key in seats:
        locks.pop(key, None)

    return ToolResult(
        status="success",
        data=order,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


# =============================================================================
# Helpers
# =============================================================================


def _generate_sessions(cinema: dict, movies: list[dict], date_str: str) -> list[dict]:
    """为影院和影片列表生成随机场次。"""
    if not movies:
        return []

    sessions = []
    halls = cinema.get("halls", [])
    if not halls:
        return []

    # 每部影片在随机几个厅有排片
    time_slots_base = [
        "10:00", "10:30", "11:00", "12:30", "13:00", "14:00",
        "14:30", "15:30", "16:00", "17:00", "17:30", "18:30",
        "19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00",
    ]

    for movie in movies[:6]:  # 最多排 6 部
        # 每个影片选 2-4 个厅
        selected_halls = random.sample(halls, min(random.randint(2, 4), len(halls)))
        for hall in selected_halls:
            start_time = random.choice(time_slots_base)
            end_h, end_m = _add_minutes(start_time, movie["duration_min"] + 15)
            hall_type = hall["type"]
            base_price = {"IMAX": 80, "杜比": 70, "VIP": 90, "激光": 55, "LUXE": 65, "4DX": 85, "ScreenX": 65, "情侣": 60}.get(hall_type, 45)

            sessions.append({
                "session_id": _make_id("ss"),
                "movie_id": movie["id"],
                "movie_title": movie["title"],
                "cinema_id": cinema["id"],
                "hall_name": hall["name"],
                "hall_type": hall_type,
                "date": date_str or datetime.now().strftime("%Y-%m-%d"),
                "start_time": start_time,
                "end_time": f"{end_h:02d}:{end_m:02d}",
                "language": random.choice(["国语", "英语", "原版"]),
                "dimension": "2D" if hall_type not in ("IMAX", "4DX") else random.choice(["2D", "3D"]),
                "base_price": base_price,
                "vip_price": base_price + random.choice([0, 10, 20]),
                "available_seats": random.randint(20, hall["capacity"]),
                "total_seats": hall["capacity"],
            })

    sessions.sort(key=lambda s: s["start_time"])
    return sessions


def _generate_seats(row_count: int, col_count: int) -> list[dict]:
    """生成座位图。"""
    seats = []
    best_rows = range(4, 9)  # 最佳观影区
    for r in range(1, row_count + 1):
        for c in range(1, col_count + 1):
            # 随机已售
            is_sold = random.random() < 0.35
            # 情侣座（最后两排靠中间）
            is_couple = r >= row_count - 2 and col_count // 2 - 2 <= c <= col_count // 2 + 1
            # 前排便宜
            price = round(random.uniform(35, 55), 1) if r <= 3 else (
                round(random.uniform(45, 65), 1) if r <= 9 else
                round(random.uniform(40, 55), 1)
            )
            seats.append({
                "row": r,
                "col": c,
                "seat_name": f"{r}排{c}座",
                "status": "sold" if is_sold and not is_couple else "available",
                "price": price,
                "is_couple_seat": is_couple,
                "is_best_area": r in best_rows and 3 <= c <= col_count - 2,
            })
    return seats


def _add_minutes(time_str: str, minutes: int) -> tuple[int, int]:
    h, m = map(int, time_str.split(":"))
    total = h * 60 + m + minutes
    return total // 60, total % 60
