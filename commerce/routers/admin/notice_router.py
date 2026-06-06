"""B端 公告管理路由."""

from fastapi import APIRouter, Body, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/notices")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_notices(request: Request) -> Result:
    return _svc(request).admin.list_notices()


@router.post("")
async def create_notice(body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.create_notice(body)


@router.delete("/{notice_id}")
async def delete_notice(notice_id: str, request: Request) -> Result:
    return _svc(request).admin.delete_notice(notice_id)
