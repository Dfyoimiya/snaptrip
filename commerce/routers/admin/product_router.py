"""B端 商品管理路由."""

from fastapi import APIRouter, Body, Query, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/products")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_products_admin(
    request: Request,
    merchant_id: str = Query(default=None),
    category_id: str = Query(default=None),
    keyword: str = Query(default=None),
    status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Result:
    return _svc(request).admin.list_products_admin(
        {
            "merchant_id": merchant_id,
            "category_id": category_id,
            "keyword": keyword,
            "status": status,
            "page": page,
            "size": size,
        }
    )


@router.post("")
async def create_product(body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.create_product(body)


@router.put("/{product_id}")
async def update_product(product_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.update_product(product_id, body)


@router.put("/{product_id}/status")
async def toggle_product_status(product_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.toggle_product_status(product_id, body["status"])


@router.put("/batch/status")
async def batch_product_status(body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.batch_product_status(body["ids"], body["status"])
