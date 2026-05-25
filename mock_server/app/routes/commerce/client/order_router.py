"""Mock Server — C端 订单路由."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, Query, Request

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.order.order import OrderCreateReq, CancelReq

from app import state
from app.middleware import get_user_from_request

router = APIRouter(prefix="/orders")
DATA = Path(__file__).parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.post("")
async def create_order(req: OrderCreateReq, request: Request) -> Result[dict]:
    uid = get_user_from_request(request)
    if not uid:
        return Result(code=ErrorCode.USER_TOKEN_INVALID, message="Token 无效")

    products = _load("seed_products.json")
    total_price = 0
    items = []
    for item_req in req.items:
        prod = next((p for p in products if p["id"] == item_req.product_id), None)
        if not prod:
            return Result(code=ErrorCode.PROD_NOT_FOUND, message=f"商品 {item_req.product_id} 不存在")
        price = prod["price"]
        items.append({
            "product_id": prod["id"], "product_name": prod["name"],
            "product_image": prod.get("image", ""), "spec_text": "", "flavor_text": "",
            "qty": item_req.qty, "price": price,
        })
        total_price += price * item_req.qty

    order_id = state.gen_uuid()
    order_no = state.gen_order_no()
    order = {
        "order_id": order_id, "order_no": order_no,
        "merchant_id": req.merchant_id,
        "merchant_name": next((m["name"] for m in _load("seed_merchants.json") if m["id"] == req.merchant_id), ""),
        "total_price": total_price, "original_price": total_price,
        "status": "PENDING", "pay_status": "UNPAID",
        "item_count": sum(i["qty"] for i in items),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_id": uid,
    }
    state._orders[order_id] = order
    state._order_items[order_id] = items
    state._order_status_logs[order_id] = [{"from_status": None, "to_status": "PENDING", "operator": uid, "remark": None, "created_at": order["created_at"]}]
    return Result(data={**order, "items": items})


@router.get("")
async def list_orders(
    request: Request,
    status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    uid = get_user_from_request(request)
    orders = [o for o in state._orders.values() if o.get("user_id") == uid] if uid else list(state._orders.values())
    if status:
        orders = [o for o in orders if o["status"] == status]
    orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    total = len(orders)
    start = (page - 1) * size
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": orders[start:start + size]})


@router.get("/{order_id}")
async def get_order(order_id: str, request: Request) -> Result[dict]:
    order = state._orders.get(order_id)
    if not order:
        return Result(code=ErrorCode.ORDER_NOT_FOUND, message="订单不存在")
    return Result(data={
        **order,
        "items": state._order_items.get(order_id, []),
        "status_logs": state._order_status_logs.get(order_id, []),
    })


@router.put("/{order_id}/cancel")
async def cancel_order(order_id: str, req: CancelReq, request: Request) -> Result[dict]:
    order = state._orders.get(order_id)
    if not order:
        return Result(code=ErrorCode.ORDER_NOT_FOUND, message="订单不存在")
    if order["status"] not in ("PENDING", "PAID"):
        return Result(code=ErrorCode.ORDER_STATUS_INVALID, message="当前状态不允许取消")
    order["status"] = "CANCELLED"
    state._order_status_logs.setdefault(order_id, []).append({
        "from_status": "PENDING", "to_status": "CANCELLED", "operator": get_user_from_request(request) or "user",
        "remark": req.reason, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    return Result(data=order)


@router.post("/{order_id}/pay")
async def pay_order(order_id: str, request: Request) -> Result[dict]:
    order = state._orders.get(order_id)
    if not order:
        return Result(code=ErrorCode.ORDER_NOT_FOUND, message="订单不存在")
    order["status"] = "PAID"
    order["pay_status"] = "PAID"
    return Result(data={"order_id": order_id, "pay_url": f"https://mock-pay.example.com/pay/{order_id}"})
