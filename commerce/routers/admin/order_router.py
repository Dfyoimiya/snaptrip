"""B端 订单管理路由."""

from fastapi import APIRouter, Body, Query, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/orders")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_orders_admin(
    request: Request,
    status: str = Query(default=None),
    keyword: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Result:
    return _svc(request).admin.list_orders_admin(
        {"status": status, "keyword": keyword, "page": page, "size": size}
    )


@router.get("/{order_id}")
async def get_order(order_id: str, request: Request) -> Result:
    return _svc(request).order.get_order(order_id)


@router.put("/{order_id}/status")
async def update_order_status(order_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.update_order_status(
        order_id, body["target_status"], "admin", body.get("remark")
    )


@router.get("/export")
async def export_orders(request: Request) -> Result:
    return _svc(request).admin.export_orders()
