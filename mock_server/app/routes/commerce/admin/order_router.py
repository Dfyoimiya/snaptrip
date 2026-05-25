"""Mock Server — B端 订单管理."""

from __future__ import annotations

import io
import time

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.order.order import OrderStatusFlowReq

from app import state

router = APIRouter(prefix="/orders")


STATUS_FLOW = {
    "PENDING": ["PAID", "CANCELLED"],
    "PAID": ["CONFIRMED", "CANCELLED"],
    "CONFIRMED": ["DELIVERING"],
    "DELIVERING": ["COMPLETED"],
}


@router.get("")
async def list_orders(
    status: str = Query(default=None),
    keyword: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    orders = list(state._orders.values())
    if status:
        orders = [o for o in orders if o["status"] == status]
    if keyword:
        orders = [o for o in orders if keyword in o.get("order_no", "") or keyword in o.get("merchant_name", "")]
    orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    total = len(orders)
    start = (page - 1) * size
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": orders[start:start + size]})


@router.get("/{order_id}")
async def get_order(order_id: str):
    order = state._orders.get(order_id)
    if not order:
        return Result(code=ErrorCode.ORDER_NOT_FOUND, message="订单不存在")
    return Result(data={**order, "items": state._order_items.get(order_id, []), "status_logs": state._order_status_logs.get(order_id, [])})


@router.put("/{order_id}/status")
async def update_order_status(order_id: str, req: OrderStatusFlowReq):
    order = state._orders.get(order_id)
    if not order:
        return Result(code=ErrorCode.ORDER_NOT_FOUND, message="订单不存在")
    allowed = STATUS_FLOW.get(order["status"], [])
    if req.target_status.value not in allowed:
        return Result(code=ErrorCode.ORDER_STATUS_INVALID, message=f"不允许从 {order['status']} 流转到 {req.target_status.value}")

    order["status"] = req.target_status.value
    state._order_status_logs.setdefault(order_id, []).append({
        "from_status": order.get("status"), "to_status": req.target_status.value,
        "operator": "admin", "remark": req.remark,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    return Result(data=order)


@router.get("/export")
async def export_orders():
    data = "order_no,status,total_price,created_at\n"
    for o in sorted(state._orders.values(), key=lambda x: x.get("created_at", ""), reverse=True):
        data += f"{o['order_no']},{o['status']},{o['total_price']},{o['created_at']}\n"
    return StreamingResponse(io.BytesIO(data.encode("utf-8")), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=orders_export.csv"})
