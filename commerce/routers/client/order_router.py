"""C端 订单路由."""

from fastapi import APIRouter, Query, Request
from contracts.schemas.common import Result
from contracts.schemas.order.order import CancelReq, OrderCreateReq

router = APIRouter(prefix="/orders")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.post("")
async def create_order(req: OrderCreateReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).order.create_order(auth, req.model_dump())


@router.get("")
async def list_orders(request: Request, status: str = Query(default=None), page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100)) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).order.list_orders(auth, {"status": status, "page": page, "size": size})


@router.get("/{order_id}")
async def get_order(order_id: str, request: Request) -> Result:
    return _svc(request).order.get_order(order_id)


@router.put("/{order_id}/cancel")
async def cancel_order(order_id: str, req: CancelReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).order.cancel_order(order_id, auth, req.reason)


@router.post("/{order_id}/pay")
async def pay_order(order_id: str, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).order.pay_order(order_id, auth)
