"""Mock Server — C端 收藏路由."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.user.auth import FavoriteAddReq, FavoriteRemoveReq

from app import state
from app.middleware import get_user_from_request

router = APIRouter(prefix="/favorites")


@router.get("")
async def list_favorites(
    request: Request,
    type: str = Query(default=None),
):
    uid = get_user_from_request(request)
    if not uid:
        return Result(code=ErrorCode.USER_TOKEN_INVALID, message="Token 无效")
    items = state._favorites.get(uid, [])
    if type:
        items = [i for i in items if i.get("target_type") == type]
    return Result(data=items)


@router.post("")
async def add_favorite(req: FavoriteAddReq, request: Request) -> Result:
    uid = get_user_from_request(request)
    if not uid:
        return Result(code=ErrorCode.USER_TOKEN_INVALID, message="Token 无效")
    if uid not in state._favorites:
        state._favorites[uid] = []
    # Idempotent
    exists = any(i["target_type"] == req.target_type and i["target_id"] == req.target_id for i in state._favorites[uid])
    if not exists:
        state._favorites[uid].append({"id": state.gen_uuid(), "target_type": req.target_type, "target_id": req.target_id, "created_at": "2024-06-01T10:00:00Z"})
    return Result(data=None)


@router.delete("")
async def remove_favorite(req: FavoriteRemoveReq, request: Request) -> Result:
    uid = get_user_from_request(request)
    if uid and uid in state._favorites:
        state._favorites[uid] = [i for i in state._favorites[uid] if not (i["target_type"] == req.target_type and i["target_id"] == req.target_id)]
    return Result(data=None)
