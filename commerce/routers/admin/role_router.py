"""B端 角色管理路由."""

from fastapi import APIRouter, Body, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/roles")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_roles(request: Request) -> Result:
    return _svc(request).admin.list_roles()


@router.post("")
async def create_role(body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.create_role(body)


@router.put("/{role_id}/permissions")
async def assign_permissions(role_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.assign_permissions(role_id, body["permission_codes"])


@router.get("/permissions/tree")
async def get_permission_tree(request: Request) -> Result:
    return _svc(request).admin.get_permission_tree()
