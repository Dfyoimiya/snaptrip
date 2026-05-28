"""C端 购物车路由."""

from fastapi import APIRouter, Request
from contracts.schemas.common import Result
from contracts.schemas.order.order import CartAddReq, CartUpdateReq

router = APIRouter(prefix="/cart")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def get_cart(request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).cart.get_cart(auth)


@router.post("")
async def add_to_cart(req: CartAddReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).cart.add_item(auth, req.product_id, req.spec_value_id, req.flavor_ids, req.qty)


@router.put("/{item_id}")
async def update_cart(item_id: str, req: CartUpdateReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).cart.update_qty(auth, item_id, req.qty)


@router.delete("/{item_id}")
async def remove_item(item_id: str, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).cart.remove_item(auth, item_id)


@router.delete("")
async def clear_cart(request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).cart.clear(auth)
