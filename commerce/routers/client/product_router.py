"""C端 商品路由."""

from fastapi import APIRouter, Query, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/products")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("/{product_id}")
async def get_product(product_id: str, request: Request) -> Result:
    return _svc(request).merchant.get_product(product_id)


@router.get("/{product_id}/reviews")
async def get_reviews(product_id: str, page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100), request: Request = None) -> Result:
    return _svc(request).review.list_reviews(product_id, page, size)


@router.get("/{product_id}/reviews/stats")
async def get_review_stats(product_id: str, request: Request) -> Result:
    return _svc(request).review.get_stats(product_id)
