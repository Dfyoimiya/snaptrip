"""B端 认证路由."""

from fastapi import APIRouter, Request
from contracts.schemas.common import Result
from contracts.schemas.admin.admin import AdminLoginReq

router = APIRouter(prefix="/auth")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.post("/login")
async def admin_login(req: AdminLoginReq, request: Request) -> Result:
    return _svc(request).admin.admin_login(req.username, req.password)
