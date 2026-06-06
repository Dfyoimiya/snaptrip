"""Mock Server — C端 认证路由."""

from __future__ import annotations

import hashlib
import time

from fastapi import APIRouter, Request
from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.user.auth import LoginReq, LoginResp, RefreshReq, RegisterReq, TokenResp, UserInfoResp
from app import state

router = APIRouter(prefix="/auth")


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _make_token(user_id: str, role: str = "customer") -> tuple[str, str, int]:
    import uuid as _uuid
    token = _uuid.uuid4().hex
    refresh = _uuid.uuid4().hex
    expires = int(time.time()) + 7200
    state._sessions[token] = {"user_id": user_id, "role": role, "expires_at": expires}
    return token, refresh, 7200


@router.post("/register")
async def register(req: RegisterReq) -> Result[LoginResp]:
    if any(u["phone"] == req.phone for u in state._users.values()):
        return Result(code=ErrorCode.USER_PHONE_EXISTS, message="该手机号已注册")

    uid = state.next_id("U")
    state._users[uid] = {
        "user_id": uid, "phone": req.phone, "password_hash": _hash_pw(req.password),
        "nickname": req.nickname, "avatar": None, "gender": None,
        "created_at": "2024-06-01T10:00:00Z",
    }
    token, refresh, exp = _make_token(uid)
    return Result(data=LoginResp(
        user_id=uid, token=token, refresh_token=refresh, expires_in=exp,
        user_info=UserInfoResp(user_id=uid, phone=req.phone[:3] + "****" + req.phone[-4:],
                               nickname=req.nickname, created_at="2024-06-01T10:00:00Z"),
    ).model_dump())


@router.post("/login")
async def login(req: LoginReq) -> Result[LoginResp]:
    user = next((u for u in state._users.values() if u["phone"] == req.phone), None)
    if not user or user["password_hash"] != _hash_pw(req.password):
        return Result(code=ErrorCode.USER_WRONG_PASSWORD, message="密码错误")

    token, refresh, exp = _make_token(user["user_id"])
    return Result(data=LoginResp(
        user_id=user["user_id"], token=token, refresh_token=refresh, expires_in=exp,
        user_info=UserInfoResp(
            user_id=user["user_id"],
            phone=user["phone"][:3] + "****" + user["phone"][-4:],
            nickname=user["nickname"], avatar=user.get("avatar"),
            gender=user.get("gender"), created_at=user["created_at"],
        ),
    ).model_dump())


@router.post("/refresh")
async def refresh(req: RefreshReq) -> Result[TokenResp]:
    token, refresh_token, exp = _make_token("mock-user")
    return Result(data=TokenResp(token=token, refresh_token=refresh_token, expires_in=exp).model_dump())


@router.post("/logout")
async def logout(request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    state._sessions.pop(token, None)
    return Result(message="已登出")
