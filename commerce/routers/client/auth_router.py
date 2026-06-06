"""C端 认证路由 — commerce package (shared by mock_server & backend)."""

from fastapi import APIRouter, Request
from contracts.schemas.common import Result
from contracts.schemas.user.auth import LoginReq, RefreshReq, RegisterReq, TokenResp, LoginResp, UserInfoResp

router = APIRouter(prefix="/auth")


def _get_svc(request: Request):
    """Service locator — injected by mock_server or backend via app.state."""
    return request.app.state.commerce_services


@router.post("/register")
async def register(req: RegisterReq, request: Request) -> Result:
    svc = _get_svc(request)
    return svc.user.register(req.phone, req.password, req.nickname)


@router.post("/login")
async def login(req: LoginReq, request: Request) -> Result:
    svc = _get_svc(request)
    return svc.user.login(req.phone, req.password)


@router.post("/refresh")
async def refresh(req: RefreshReq, request: Request) -> Result:
    svc = _get_svc(request)
    return svc.user.refresh_token(req.refresh_token)


@router.post("/logout")
async def logout(request: Request) -> Result:
    svc = _get_svc(request)
    return svc.user.logout(request.headers.get("Authorization", ""))
