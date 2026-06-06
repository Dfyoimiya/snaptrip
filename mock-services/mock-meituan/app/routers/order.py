"""通用订单路由 —— 支付/查询/取消/退款。

支持所有订单类型（餐厅/外卖/电影/酒店/娱乐）。

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.schemas import ToolResult

router = APIRouter(prefix="/order", tags=["order"])

_prepare_store: dict[str, dict] = {}
_order_store: dict[str, dict] = {}


@router.post("/prepare")
async def order_prepare(body: dict):
    """通用下单准备。

    接受任意订单类型，创建预订单（15分钟过期）。
    """
    t0 = time.perf_counter()
    prepare_id = f"prep_{uuid.uuid4().hex[:12]}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    record = {
        "prepare_id": prepare_id,
        "order_type": body.get("order_type", "general"),
        "poi_id": body.get("poi_id", ""),
        "items": body.get("items", []),
        "user_id": body.get("user_id", ""),
        "total_price": round(body.get("total_price", random.uniform(20, 300)), 2),
        "status": "prepared",
        "expires_at": expires_at.isoformat(),
    }
    _prepare_store[prepare_id] = record

    return ToolResult(
        status="success",
        data={
            "prepare_id": prepare_id,
            "total_price": record["total_price"],
            "expires_at": record["expires_at"],
            "expires_in_seconds": 900,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/submit")
async def order_submit(body: dict):
    """通用下单提交。"""
    t0 = time.perf_counter()
    prepare_id = body.get("prepare_id", "")

    # 如果有 prepare_id，验证
    if prepare_id:
        record = _prepare_store.get(prepare_id)
        if record is None:
            return ToolResult(
                status="failure",
                error_code="INVALID_PREPARE_ID",
                error_message="prepare_id 不存在或已过期",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            ).model_dump()
        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            del _prepare_store[prepare_id]
            return ToolResult(
                status="failure",
                error_code="PREPARE_EXPIRED",
                error_message="预订单已过期",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            ).model_dump()
        total_price = record["total_price"]
        del _prepare_store[prepare_id]
    else:
        total_price = body.get("total_price", random.uniform(20, 300))

    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    order = {
        "order_id": order_id,
        "order_type": body.get("order_type", "general"),
        "poi_id": body.get("poi_id", ""),
        "user_id": body.get("user_id", ""),
        "items": body.get("items", []),
        "total_price": total_price,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paid_at": None,
        "cancelled_at": None,
        "refund_id": None,
    }
    _order_store[order_id] = order

    return ToolResult(
        status="success",
        data={
            "order_id": order_id,
            "status": "confirmed",
            "total_price": total_price,
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/pay")
async def order_pay(body: dict):
    """支付订单。"""
    t0 = time.perf_counter()
    order_id = body.get("order_id", "")
    amount = body.get("amount", 0)
    pay_method = body.get("pay_method", "wechat")

    order = _order_store.get(order_id)
    if order is None:
        return ToolResult(
            status="failure",
            error_code="INVALID_ORDER_ID",
            error_message="订单不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    if order["status"] == "paid":
        return ToolResult(
            status="failure",
            error_code="ALREADY_PAID",
            error_message="订单已支付",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    # 10% 随机支付失败
    if random.random() < 0.10:
        return ToolResult(
            status="failure",
            error_code="PAYMENT_FAILED",
            error_message="支付失败，请重试",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    order["status"] = "paid"
    order["paid_at"] = datetime.now(timezone.utc).isoformat()
    order["payment_id"] = payment_id
    order["pay_method"] = pay_method
    order["paid_amount"] = amount or order["total_price"]

    return ToolResult(
        status="success",
        data={
            "order_id": order_id,
            "payment_id": payment_id,
            "amount": order["paid_amount"],
            "pay_method": pay_method,
            "status": "paid",
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.get("/{order_id}")
async def get_order(order_id: str):
    """查询订单详情。"""
    t0 = time.perf_counter()
    order = _order_store.get(order_id)
    if order is None:
        return ToolResult(
            status="failure",
            error_code="ORDER_NOT_FOUND",
            error_message=f"订单 {order_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    return ToolResult(
        status="success",
        data=order,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: str, body: dict = None):
    """取消订单。"""
    t0 = time.perf_counter()
    order = _order_store.get(order_id)
    if order is None:
        return ToolResult(
            status="failure",
            error_code="ORDER_NOT_FOUND",
            error_message=f"订单 {order_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    if order["status"] in ("cancelled", "refunded", "completed"):
        return ToolResult(
            status="failure",
            error_code="CANNOT_CANCEL",
            error_message=f"订单状态为 {order['status']}，不可取消",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    order["status"] = "cancelled"
    order["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    order["cancel_reason"] = (body or {}).get("reason", "用户主动取消")

    return ToolResult(
        status="success",
        data={"order_id": order_id, "status": "cancelled"},
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()


@router.post("/{order_id}/refund")
async def refund_order(order_id: str, body: dict = None):
    """退款。"""
    t0 = time.perf_counter()
    order = _order_store.get(order_id)
    if order is None:
        return ToolResult(
            status="failure",
            error_code="ORDER_NOT_FOUND",
            error_message=f"订单 {order_id} 不存在",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    if order["status"] != "paid":
        return ToolResult(
            status="failure",
            error_code="CANNOT_REFUND",
            error_message=f"订单状态为 {order['status']}，不可退款",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        ).model_dump()

    refund_id = f"ref_{uuid.uuid4().hex[:12]}"
    order["status"] = "refunded"
    order["refund_id"] = refund_id
    order["refund_reason"] = (body or {}).get("reason", "用户申请退款")
    order["refund_amount"] = (body or {}).get("amount", order.get("paid_amount", order["total_price"]))

    return ToolResult(
        status="success",
        data={
            "order_id": order_id,
            "refund_id": refund_id,
            "refund_amount": order["refund_amount"],
            "status": "refunded",
        },
        latency_ms=int((time.perf_counter() - t0) * 1000),
    ).model_dump()
