"""Mock Server — C端 评价路由."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.product.product import ReviewCreateReq

from app import state
from app.middleware import get_user_from_request

router = APIRouter(prefix="/reviews")


@router.post("")
async def create_review(req: ReviewCreateReq, request: Request) -> Result[dict]:
    uid = get_user_from_request(request)
    if not uid:
        return Result(code=ErrorCode.USER_TOKEN_INVALID, message="Token 无效")

    # Check if already reviewed this order
    existing = [r for r in state._reviews if r.get("user_id") == uid and r.get("order_id") == req.order_id]
    if existing:
        return Result(code=ErrorCode.REVW_ALREADY_EXISTS, message="该订单已评价")

    review = {
        "id": state.gen_uuid(),
        "user_id": uid,
        "user_nickname": state._users.get(uid, {}).get("nickname", "匿名用户"),
        "user_avatar": state._users.get(uid, {}).get("avatar"),
        "product_id": req.product_id,
        "order_id": req.order_id,
        "rating": req.rating,
        "content": req.content,
        "images": req.images,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    state._reviews.append(review)
    return Result(data=review)
