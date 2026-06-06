"""Mock Server — C端 地址路由."""

from __future__ import annotations

from fastapi import APIRouter, Request

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.user.auth import AddressCreateReq, AddressUpdateReq, AddressResp

from app import state
from app.middleware import get_user_from_request

router = APIRouter(prefix="/addresses")


@router.get("")
async def list_addresses(request: Request) -> Result[dict]:
    uid = get_user_from_request(request)
    if not uid:
        return Result(code=ErrorCode.USER_TOKEN_INVALID, message="Token 无效")
    items = state._addresses.get(uid, [])
    return Result(data=items)


@router.post("")
async def create_address(req: AddressCreateReq, request: Request) -> Result[dict]:
    uid = get_user_from_request(request)
    if not uid:
        return Result(code=ErrorCode.USER_TOKEN_INVALID, message="Token 无效")
    if uid not in state._addresses:
        state._addresses[uid] = []
    if len(state._addresses[uid]) >= 20:
        return Result(code=ErrorCode.ADDR_LIMIT_REACHED, message="最多添加20个地址")
    addr = {
        "id": state.gen_uuid(),
        "contact_name": req.contact_name,
        "phone": req.phone,
        "province": req.province,
        "city": req.city,
        "district": req.district,
        "detail": req.detail,
        "lng": req.lng,
        "lat": req.lat,
        "is_default": len(state._addresses[uid]) == 0,
        "label": req.label,
    }
    state._addresses[uid].append(addr)
    return Result(data=addr)


@router.put("/{address_id}")
async def update_address(address_id: str, req: AddressUpdateReq, request: Request) -> Result[dict]:
    uid = get_user_from_request(request)
    items = state._addresses.get(uid, []) if uid else []
    for addr in items:
        if addr["id"] == address_id:
            for field in ("contact_name", "phone", "province", "city", "district", "detail", "lng", "lat", "label"):
                val = getattr(req, field, None)
                if val is not None:
                    addr[field] = val
            return Result(data=addr)
    return Result(code=ErrorCode.ADDR_NOT_FOUND, message="地址不存在")


@router.delete("/{address_id}")
async def delete_address(address_id: str, request: Request) -> Result:
    uid = get_user_from_request(request)
    if uid and uid in state._addresses:
        state._addresses[uid] = [a for a in state._addresses[uid] if a["id"] != address_id]
    return Result(message="已删除")


@router.put("/{address_id}/default")
async def set_default(address_id: str, request: Request) -> Result:
    uid = get_user_from_request(request)
    items = state._addresses.get(uid, []) if uid else []
    for addr in items:
        addr["is_default"] = (addr["id"] == address_id)
    return Result(data=next((a for a in items if a["id"] == address_id), {}))
