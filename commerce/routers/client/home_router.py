"""C端 首页路由."""

from fastapi import APIRouter, Query, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/home")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("/banners")
async def banners(request: Request) -> Result:
    return _svc(request).home.get_banners()


@router.get("/categories")
async def categories(request: Request) -> Result:
    return _svc(request).home.get_categories()


@router.get("/recommend")
async def recommend(
    request: Request,
    lat: float = Query(default=39.9),
    lng: float = Query(default=116.4),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Result:
    return _svc(request).home.get_recommend(lat, lng, page, size)
