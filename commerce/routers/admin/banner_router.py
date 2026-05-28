"""B端 轮播图管理路由."""

from fastapi import APIRouter, Body, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/banners")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_banners(request: Request) -> Result:
    return _svc(request).admin.list_banners()


@router.post("")
async def create_banner(body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.create_banner(body)


@router.put("/{banner_id}")
async def update_banner(banner_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.update_banner(banner_id, body)


@router.delete("/{banner_id}")
async def delete_banner(banner_id: str, request: Request) -> Result:
    return _svc(request).admin.delete_banner(banner_id)
