"""订单路由 —— 模拟美团下单流程: prepare → submit → pay。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.schemas import ToolResult

router = APIRouter(prefix="/order", tags=["order"])

_pending: dict[str, dict] = {}
_confirmed: dict[str, dict] = {}


@router.post("/prepare")
async def order_prepare(body: dict):
    t0 = time.perf_counter()
    prepare_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    _pending[prepare_id] = {
        "prepare_id": prepare_id,
        "poi_id": body.get("poi_id", ""),
        "items": body.get("items", []),
        "user_id": body.get("user_id", ""),
        "status": "prepared",
        "expires_at": expires_at.isoformat(),
        "total_price": round(random.uniform(20, 300), 2),
    }

    return ToolResult(
        status="success",
        data={
            "prepare_id": prepare_id,
            "total_price": _pending[prepare_id]["total_price"],
            "expires_at": _pending[prepare_id]["expires_at"],
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/submit")
async def order_submit(body: dict):
    t0 = time.perf_counter()
    prepare_id = body.get("prepare_id", "")

    record = _pending.get(prepare_id)
    if record is None:
        return ToolResult(
            status="failure",
            error_code="INVALID_PREPARE_ID",
            error_message="prepare_id 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _pending[prepare_id]
        return ToolResult(
            status="failure",
            error_code="PREPARE_EXPIRED",
            error_message="prepare 已过期",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    order_id = str(uuid.uuid4())
    record["order_id"] = order_id
    record["status"] = "confirmed"
    _confirmed[order_id] = record
    del _pending[prepare_id]

    return ToolResult(
        status="success",
        data={
            "order_id": order_id,
            "status": "confirmed",
            "total_price": record["total_price"],
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/pay")
async def order_pay(body: dict):
    t0 = time.perf_counter()
    order_id = body.get("order_id", "")
    amount = body.get("amount", 0)

    record = _confirmed.get(order_id)
    if record is None:
        return ToolResult(
            status="failure",
            error_code="INVALID_ORDER_ID",
            error_message="order_id 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    if random.random() < 0.10:
        return ToolResult(
            status="failure",
            data={"order_id": order_id},
            error_code="PAYMENT_FAILED",
            error_message="支付失败，请重试",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    payment_id = str(uuid.uuid4())
    record["status"] = "paid"
    record["payment_id"] = payment_id

    return ToolResult(
        status="success",
        data={
            "order_id": order_id,
            "payment_id": payment_id,
            "amount": amount,
            "status": "paid",
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()
