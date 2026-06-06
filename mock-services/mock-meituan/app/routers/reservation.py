"""餐厅预订路由 —— 订座/取消。

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import random
import time
import uuid

from fastapi import APIRouter

from app.schemas import ToolResult

router = APIRouter(prefix="/reservation", tags=["reservation"])

_reservations: dict[str, dict] = {}


@router.get("/{poi_id}/slots")
async def get_reservation_slots(
    poi_id: str,
    date: str = "",
    party_size: int = 2,
):
    """查询可预订时段和桌型。"""
    t0 = time.perf_counter()

    # 时段范围
    time_slots = []
    for h in range(11, 14):
        for m in [0, 30]:
            time_slots.append({
                "time": f"{h:02d}:{m:02d}",
                "available": random.random() > 0.3,
                "remaining_tables": random.randint(0, 5),
            })
    for h in range(17, 21):
        for m in [0, 30]:
            time_slots.append({
                "time": f"{h:02d}:{m:02d}",
                "available": random.random() > 0.4,
                "remaining_tables": random.randint(0, 5),
            })

    # 桌型
    table_types = [
        {"type": "hall", "name": "大厅", "min_party": 1, "max_party": 6, "available": True},
        {"type": "private_room", "name": "包间", "min_party": 4, "max_party": 15,
         "available": party_size >= 4 and random.random() > 0.5,
         "min_consumption": random.choice([300, 500, 800])},
        {"type": "outdoor", "name": "露台", "min_party": 1, "max_party": 4,
         "available": random.random() > 0.6},
    ]

    return ToolResult(
        status="success",
        data={
            "poi_id": poi_id,
            "date": date,
            "party_size": party_size,
            "time_slots": time_slots,
            "table_types": table_types,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/create")
async def create_reservation(body: dict):
    """创建预订。"""
    t0 = time.perf_counter()

    reservation_id = f"res_{uuid.uuid4().hex[:10]}"
    record = {
        "reservation_id": reservation_id,
        "poi_id": body.get("poi_id", ""),
        "user_id": body.get("user_id", ""),
        "date": body.get("date", ""),
        "time_slot": body.get("time_slot", ""),
        "party_size": body.get("party_size", 2),
        "table_type": body.get("table_type", "hall"),
        "contact_name": body.get("contact_name", ""),
        "contact_phone": body.get("contact_phone", ""),
        "status": "confirmed",
        "table_no": f"{random.choice('ABCD')}{random.randint(1, 30)}",
    }
    _reservations[reservation_id] = record

    return ToolResult(
        status="success",
        data=record,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/{reservation_id}")
async def get_reservation(reservation_id: str):
    """查询预订详情。"""
    t0 = time.perf_counter()
    record = _reservations.get(reservation_id)
    if record is None:
        return ToolResult(
            status="failure",
            error_code="RESERVATION_NOT_FOUND",
            error_message=f"预订 {reservation_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()
    return ToolResult(
        status="success",
        data=record,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/{reservation_id}/cancel")
async def cancel_reservation(reservation_id: str, body: dict = None):
    """取消预订。"""
    t0 = time.perf_counter()
    record = _reservations.get(reservation_id)
    if record is None:
        return ToolResult(
            status="failure",
            error_code="RESERVATION_NOT_FOUND",
            error_message=f"预订 {reservation_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    if record["status"] == "cancelled":
        return ToolResult(
            status="failure",
            error_code="ALREADY_CANCELLED",
            error_message="该预订已取消",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    record["status"] = "cancelled"
    record["cancel_reason"] = (body or {}).get("reason", "用户主动取消")

    return ToolResult(
        status="success",
        data={"reservation_id": reservation_id, "status": "cancelled"},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()
