"""C端 地址路由."""

from fastapi import APIRouter, Request
from contracts.schemas.common import Result
from contracts.schemas.user.auth import AddressCreateReq, AddressUpdateReq

router = APIRouter(prefix="/addresses")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_addresses(request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).address.list_addresses(auth)


@router.post("")
async def create_address(req: AddressCreateReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).address.create_address(auth, req.model_dump())


@router.put("/{address_id}")
async def update_address(address_id: str, req: AddressUpdateReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).address.update_address(auth, address_id, req.model_dump(exclude_none=True))


@router.delete("/{address_id}")
async def delete_address(address_id: str, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).address.delete_address(auth, address_id)


@router.put("/{address_id}/default")
async def set_default(address_id: str, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).address.set_default(auth, address_id)
