"""C端 商家路由."""

from fastapi import APIRouter, Query, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/merchants")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_merchants(
    request: Request,
    lat: float = Query(default=None),
    lng: float = Query(default=None),
    category_id: str = Query(default=None),
    sort_field: str = Query(default="distance"),
    sort_order: str = Query(default="asc"),
    keyword: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Result:
    return _svc(request).merchant.list_merchants(
        {"lat": lat, "lng": lng, "category_id": category_id, "sort_field": sort_field,
         "sort_order": sort_order, "keyword": keyword, "page": page, "size": size})


@router.get("/{merchant_id}")
async def get_merchant(merchant_id: str, request: Request) -> Result:
    return _svc(request).merchant.get_merchant(merchant_id)
