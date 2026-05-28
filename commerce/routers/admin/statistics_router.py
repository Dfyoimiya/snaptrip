"""B端 统计路由."""

from fastapi import APIRouter, Query, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/statistics")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("/revenue")
async def get_revenue_stats(
    request: Request,
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
) -> Result:
    return _svc(request).admin.get_revenue_stats(start_date, end_date)


@router.get("/orders")
async def get_order_stats(
    request: Request,
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
) -> Result:
    return _svc(request).admin.get_order_stats(start_date, end_date)


@router.get("/users")
async def get_user_stats(
    request: Request,
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
) -> Result:
    return _svc(request).admin.get_user_stats(start_date, end_date)


@router.get("/ranking")
async def get_product_ranking(
    request: Request,
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
    limit: int = Query(default=10),
) -> Result:
    return _svc(request).admin.get_product_ranking(start_date, end_date, limit)
