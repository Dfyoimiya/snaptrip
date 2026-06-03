"""POI 增强路由 —— 菜单查询 + 排队取号。

基于高德真实 POI ID，动态生成菜单和排队数据。

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import random
import time
import uuid

from fastapi import APIRouter, Query

from app.core.menu_templates import generate_menu
from app.schemas import ToolResult

router = APIRouter(prefix="/poi", tags=["poi"])

# 排队状态（进程内存储）
_queue_store: dict[str, dict] = {}


@router.get("/{poi_id}/menu")
async def get_menu(
    poi_id: str,
    poi_type: str = Query("", description="高德 POI 类型，如 '中餐厅;火锅'"),
    poi_name: str = Query("", description="POI 名称"),
    is_takeout: bool = Query(False, description="是否为外卖菜单"),
):
    """根据 POI ID 和类型动态生成菜单。"""
    t0 = time.perf_counter()
    menu = generate_menu(poi_type=poi_type, poi_name=poi_name, is_takeout=is_takeout)
    menu["poi_id"] = poi_id
    return ToolResult(
        status="success",
        data=menu,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/{poi_id}/queue")
async def check_queue(
    poi_id: str,
    poi_rating: float = Query(4.0, description="高德评分 0-5"),
    date: str = Query(""),
    party_size: int = Query(2),
):
    """查询排队状态 + 在线取号。基于评分和时段动态计算。"""
    t0 = time.perf_counter()

    # 根据评分和当前时段估算排队
    hour = _current_hour()
    is_peak = (11 <= hour <= 13) or (17 <= hour <= 20)
    rating_factor = max(0, (poi_rating - 3.0) / 2.0)  # 3.0→0, 5.0→1.0

    base_wait = random.randint(0, 15)
    peak_bonus = random.randint(10, 30) if is_peak else 0
    rating_bonus = int(rating_factor * random.randint(5, 20))
    wait_minutes = min(base_wait + peak_bonus + rating_bonus, 60)

    queue_length = max(0, int(wait_minutes * random.uniform(0.5, 1.5)))
    can_take = wait_minutes < 45

    # 可预约时段
    available_slots = []
    if can_take:
        slots_pool = [
            "11:00", "11:30", "12:00", "12:30", "13:00", "13:30",
            "17:30", "18:00", "18:30", "19:00", "19:30", "20:00",
        ]
        available_slots = [s for s in slots_pool if random.random() > 0.4]

    # 记录排队号
    ticket_no = None
    if can_take:
        ticket_no = f"Q{random.randint(100, 999)}"
        _queue_store[ticket_no] = {
            "poi_id": poi_id,
            "party_size": party_size,
            "wait_minutes": wait_minutes,
            "created_at": time.time(),
        }

    return ToolResult(
        status="success",
        data={
            "poi_id": poi_id,
            "party_size": party_size,
            "wait_minutes": wait_minutes,
            "queue_length": queue_length,
            "is_peak_hour": is_peak,
            "can_take_number_online": can_take,
            "ticket_no": ticket_no,
            "available_slots": available_slots,
            "estimated_seated": (
                f"{_pad_time(hour + (wait_minutes // 60) + 1)}:{_pad_time((wait_minutes % 60))}"
                if can_take else None
            ),
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/{poi_id}/queue/take")
async def take_queue_number(
    poi_id: str,
    body: dict,
):
    """在线取号。"""
    t0 = time.perf_counter()
    party_size = body.get("party_size", 2)
    ticket_no = f"Q{random.randint(100, 999)}"
    wait_minutes = random.randint(10, 40)

    _queue_store[ticket_no] = {
        "poi_id": poi_id,
        "party_size": party_size,
        "wait_minutes": wait_minutes,
        "status": "waiting",
        "created_at": time.time(),
    }

    return ToolResult(
        status="success",
        data={
            "ticket_no": ticket_no,
            "poi_id": poi_id,
            "party_size": party_size,
            "wait_minutes": wait_minutes,
            "current_no": f"Q{random.randint(50, int(ticket_no[1:]) - 1)}",
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


def _current_hour() -> int:
    from datetime import datetime
    return datetime.now().hour


def _pad_time(v: int) -> str:
    return f"{min(v, 23):02d}"
