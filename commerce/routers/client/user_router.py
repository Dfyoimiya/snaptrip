"""C端 用户路由."""

from fastapi import APIRouter, Request
from contracts.schemas.common import Result
from contracts.schemas.user.auth import UserUpdateReq

router = APIRouter(prefix="/users")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("/me")
async def get_profile(request: Request) -> Result:
    return _svc(request).user.get_profile(request.headers.get("Authorization", ""))


@router.put("/me")
async def update_profile(req: UserUpdateReq, request: Request) -> Result:
    return _svc(request).user.update_profile(request.headers.get("Authorization", ""), req.model_dump(exclude_none=True))
