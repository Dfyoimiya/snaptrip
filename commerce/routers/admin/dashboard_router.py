"""B端 仪表盘路由."""

from fastapi import APIRouter, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/dashboard")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def get_dashboard(request: Request) -> Result:
    return _svc(request).admin.get_dashboard()
