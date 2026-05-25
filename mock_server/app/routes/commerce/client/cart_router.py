"""Mock Server — C端 购物车路由."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Request

from contracts.schemas.common import Result
from contracts.schemas.order.order import CartAddReq, CartUpdateReq
from contracts.schemas.errors import ErrorCode

from app import state
from app.middleware import get_user_from_request

router = APIRouter(prefix="/cart")
DATA = Path(__file__).parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("")
async def get_cart(request: Request) -> Result[dict]:
    uid = get_user_from_request(request)
    items = state._carts.get(uid, []) if uid else []
    return Result(data=items)


@router.post("")
async def add_to_cart(req: CartAddReq, request: Request) -> Result[dict]:
    uid = get_user_from_request(request)
    if not uid:
        return Result(code=ErrorCode.USER_TOKEN_INVALID, message="Token 无效")

    # Check product exists
    products = _load("seed_products.json")
    prod = next((p for p in products if p["id"] == req.product_id), None)
    if not prod:
        return Result(code=ErrorCode.PROD_NOT_FOUND, message="商品不存在")

    if uid not in state._carts:
        state._carts[uid] = []

    # Check if same product+spec already in cart → merge
    existing = next((c for c in state._carts[uid] if c["product_id"] == req.product_id and c.get("spec_value_id") == req.spec_value_id), None)
    if existing:
        existing["qty"] += req.qty
        return Result(data=existing)

    item = {
        "item_id": state.gen_uuid(),
        "product_id": req.product_id,
        "merchant_id": prod.get("merchant_id", ""),
        "product_name": prod["name"],
        "product_image": prod.get("image", ""),
        "spec_value_id": req.spec_value_id,
        "spec_text": "",
        "flavor_text": "",
        "price": prod["price"],
        "qty": req.qty,
        "stock": prod.get("stock", 999),
    }
    state._carts[uid].append(item)
    return Result(data=item)


@router.put("/{item_id}")
async def update_cart(item_id: str, req: CartUpdateReq, request: Request) -> Result[dict]:
    uid = get_user_from_request(request)
    items = state._carts.get(uid, []) if uid else []
    for item in items:
        if item["item_id"] == item_id:
            item["qty"] = req.qty
            return Result(data=item)
    return Result(code=ErrorCode.CART_ITEM_INVALID, message="购物车商品不存在")


@router.delete("/{item_id}")
async def remove_cart_item(item_id: str, request: Request) -> Result:
    uid = get_user_from_request(request)
    if uid and uid in state._carts:
        state._carts[uid] = [c for c in state._carts[uid] if c["item_id"] != item_id]
    return Result(message="已删除")


@router.delete("")
async def clear_cart(request: Request) -> Result:
    uid = get_user_from_request(request)
    if uid:
        state._carts[uid] = []
    return Result(message="购物车已清空")
