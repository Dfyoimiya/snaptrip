"""Mock Server — C端 用户路由."""

from __future__ import annotations

from fastapi import APIRouter, Request

from contracts.schemas.common import Result
from contracts.schemas.user.auth import UserInfoResp, UserUpdateReq

from app import state

router = APIRouter(prefix="/users")


def _get_user_id(request: Request) -> str | None:
    from app.middleware import get_user_from_request
    return get_user_from_request(request)


@router.get("/me")
async def get_profile(request: Request) -> Result[dict]:
    uid = _get_user_id(request)
    user = state._users.get(uid, {}) if uid else {}
    if not user:
        return Result(code=1006, message="Token 无效")
    return Result(data={
        "user_id": user["user_id"],
        "phone": user["phone"][:3] + "****" + user["phone"][-4:],
        "nickname": user["nickname"],
        "avatar": user.get("avatar"),
        "gender": user.get("gender"),
        "created_at": user["created_at"],
    })


@router.put("/me")
async def update_profile(req: UserUpdateReq, request: Request) -> Result[dict]:
    uid = _get_user_id(request)
    if uid and uid in state._users:
        if req.nickname is not None:
            state._users[uid]["nickname"] = req.nickname
        if req.avatar is not None:
            state._users[uid]["avatar"] = req.avatar
        if req.gender is not None:
            state._users[uid]["gender"] = req.gender
    return await get_profile(request)
