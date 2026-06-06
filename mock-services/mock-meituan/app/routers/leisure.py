"""休闲娱乐路由 —— KTV/密室/剧本杀/桌游/酒吧 搜索与预订。

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import math
import random
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Query

from app.schemas import ToolResult, _make_id

router = APIRouter(prefix="/leisure", tags=["leisure"])

_bookings: dict[str, dict] = {}


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("/search")
async def search_leisure(
    lat: float = Query(39.9),
    lng: float = Query(116.4),
    radius: float = Query(5.0),
    category: str = Query("", description="KTV/密室/剧本杀/桌游/酒吧"),
    keyword: str = Query(""),
    limit: int = Query(20, le=30),
):
    """搜索休闲娱乐场所。"""
    t0 = time.perf_counter()

    all_cats = ["KTV", "密室逃脱", "剧本杀", "桌游", "酒吧", "LiveHouse"]
    if category:
        all_cats = [c for c in all_cats if category in c]

    venues = []
    for i in range(random.randint(8, min(limit, 20))):
        cat = random.choice(all_cats)
        dist = round(random.uniform(0.2, radius), 1)
        venues.append({
            "id": f"lei_{uuid.uuid4().hex[:8]}",
            "name": _rand_venue_name(cat),
            "category": cat,
            "distance_km": dist,
            "avg_rating": round(random.uniform(3.5, 5.0), 1),
            "price_level": random.randint(1, 4),
            "open_hours": "10:00-02:00" if cat != "密室逃脱" else "10:00-22:00",
            "tags": _rand_tags(cat),
            "address": f"附近XX路{random.randint(10, 500)}号",
        })

    if keyword:
        venues = [v for v in venues if keyword in v["name"] or keyword in v["category"]]

    venues.sort(key=lambda x: x["distance_km"])
    return ToolResult(
        status="success",
        data={"venues": venues, "total": len(venues)},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/{venue_id}/slots")
async def get_venue_slots(
    venue_id: str,
    date: str = "",
    party_size: int = Query(4),
):
    """查询可预订时段。"""
    t0 = time.perf_counter()

    time_slots = []
    for h in range(10, 23):
        for m in [0, 30]:
            time_slots.append({
                "time": f"{h:02d}:{m:02d}",
                "available": random.random() > 0.35,
                "price": round(random.uniform(68, 298), 1),
                "room_type": random.choice(["小包", "中包", "大包", "豪华包"]),
                "remaining": random.randint(0, 5),
            })

    return ToolResult(
        status="success",
        data={
            "venue_id": venue_id,
            "date": date,
            "party_size": party_size,
            "time_slots": time_slots,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/booking/create")
async def create_booking(body: dict):
    """预订娱乐场所。"""
    t0 = time.perf_counter()

    booking_id = _make_id("lbk")
    record = {
        "booking_id": booking_id,
        "venue_id": body.get("venue_id", ""),
        "date": body.get("date", ""),
        "time_slot": body.get("time_slot", ""),
        "party_size": body.get("party_size", 4),
        "room_type": body.get("room_type", "中包"),
        "price": body.get("price", 128),
        "status": "confirmed",
        "confirm_code": f"LS{random.randint(1000, 9999)}",
        "created_at": datetime.now().isoformat(),
    }
    _bookings[booking_id] = record

    return ToolResult(
        status="success",
        data=record,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/booking/{booking_id}/cancel")
async def cancel_booking(booking_id: str, body: dict = None):
    """取消娱乐预订。"""
    t0 = time.perf_counter()
    record = _bookings.get(booking_id)
    if record is None:
        return ToolResult(
            status="failure",
            error_code="BOOKING_NOT_FOUND",
            error_message=f"预订 {booking_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    record["status"] = "cancelled"
    return ToolResult(
        status="success",
        data={"booking_id": booking_id, "status": "cancelled"},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


def _rand_venue_name(cat: str) -> str:
    prefixes = {
        "KTV": ["好乐迪", "纯K", "星聚会", "魅KTV", "唱吧"],
        "密室逃脱": ["X先生", "长藤鬼校", "屋有岛", "EGA", "奥秘之家"],
        "剧本杀": ["NINES", "推理大师", "我是谜", "戏局", "迷雾"],
        "桌游": ["猎人", "女仆", "猫の", "齿轮", "骰子"],
        "酒吧": ["公社", "天堂", "公路", "隐", "渡"],
        "LiveHouse": ["MAO", "疆进酒", "乐空间", "黄昏", "DDC"],
    }
    suffixes = {
        "KTV": ["KTV", "量贩KTV", "Party K"],
        "密室逃脱": ["密室逃脱", "沉浸式密室", "实景密室"],
        "剧本杀": ["剧本杀", "推理馆", "沉浸式剧场"],
        "桌游": ["桌游吧", "轰趴馆", "游戏社"],
        "酒吧": ["酒吧", "精酿啤酒吧", "Cocktail Bar", "Whisky Bar"],
        "LiveHouse": ["LiveHouse", "音乐现场", "Live"],
    }
    prefix = random.choice(prefixes.get(cat, ["XX"]))
    suffix = random.choice(suffixes.get(cat, ["娱乐"]))
    return f"{prefix}{suffix}"


def _rand_tags(cat: str) -> list[str]:
    tag_map = {
        "KTV": ["音效好", "歌全", "性价比高", "环境好", "连锁"],
        "密室逃脱": ["恐怖", "机械", "NPC", "沉浸式", "非恐"],
        "剧本杀": ["情感本", "硬核本", "恐怖本", "欢乐本", "沉浸式"],
        "桌游": ["狼人杀", "三国杀", "UNO", "Switch", "PS5"],
        "酒吧": ["精酿", "鸡尾酒", "驻唱", "露台", "安静"],
        "LiveHouse": ["摇滚", "民谣", "爵士", "电子", "独立音乐"],
    }
    return random.sample(tag_map.get(cat, ["热门"]), k=random.randint(2, 4))
