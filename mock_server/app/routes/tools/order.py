"""Mock Server — tool routes: order flow (prepare → submit → pay)."""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.schemas import ToolResult

router = APIRouter()
_pending: dict[str, dict] = {}
_confirmed: dict[str, dict] = {}
_paid: dict[str, dict] = {}


@router.post("/order/prepare")
async def order_prepare(body: dict):
    t0 = time.perf_counter()
    prepare_id = uuid.uuid4().hex[:12]
    record = {
        "prepare_id": prepare_id,
        "poi_id": body.get("poi_id", ""),
        "items": body.get("items", []),
        "user_id": body.get("user_id", ""),
        "status": "prepared",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        "total_price": random.randint(20, 300),
    }
    _pending[prepare_id] = record
    elapsed = int((time.perf_counter() - t0) * 1000)
    return ToolResult(
        status="success",
        data={"prepare_id": prepare_id, "total_price": record["total_price"], "expires_at": record["expires_at"]},
        latency_ms=elapsed,
    )


@router.post("/order/submit")
async def order_submit(body: dict):
    t0 = time.perf_counter()
    prepare_id = body.get("prepare_id", "")
    record = _pending.get(prepare_id)
    if not record:
        return ToolResult(
            status="failure",
            error_code="INVALID_PREPARE_ID",
            error_message="Prepare order not found or expired",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
    if datetime.fromisoformat(record["expires_at"]) < datetime.now(timezone.utc):
        del _pending[prepare_id]
        return ToolResult(status="failure", error_code="PREPARE_EXPIRED", error_message="Prepare order expired")

    order_id = uuid.uuid4().hex[:12]
    record["order_id"] = order_id
    record["status"] = "confirmed"
    _confirmed[order_id] = record
    del _pending[prepare_id]
    elapsed = int((time.perf_counter() - t0) * 1000)
    return ToolResult(
        status="success",
        data={"order_id": order_id, "status": "confirmed", "total_price": record["total_price"]},
        latency_ms=elapsed,
    )


@router.post("/order/pay")
async def order_pay(body: dict):
    t0 = time.perf_counter()
    order_id = body.get("order_id", "")
    record = _confirmed.get(order_id)
    if not record:
        return ToolResult(status="failure", error_code="INVALID_ORDER_ID", error_message="Order not found")

    if random.random() < 0.1:
        return ToolResult(status="failure", error_code="PAYMENT_FAILED", error_message="Payment gateway declined")

    payment_id = uuid.uuid4().hex[:12]
    record["payment_id"] = payment_id
    record["status"] = "paid"
    _paid[order_id] = record
    del _confirmed[order_id]
    elapsed = int((time.perf_counter() - t0) * 1000)
    return ToolResult(
        status="success",
        data={"order_id": order_id, "payment_id": payment_id, "amount": body.get("amount", 0), "status": "paid"},
        latency_ms=elapsed,
    )
