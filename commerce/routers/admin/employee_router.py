"""B端 员工管理路由."""

from fastapi import APIRouter, Body, Query, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/employees")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_employees(
    request: Request,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Result:
    return _svc(request).admin.list_employees(page, size)


@router.post("")
async def create_employee(body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.create_employee(body)


@router.put("/{employee_id}")
async def update_employee(employee_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.update_employee(employee_id, body)


@router.delete("/{employee_id}")
async def delete_employee(employee_id: str, request: Request) -> Result:
    return _svc(request).admin.delete_employee(employee_id)


@router.put("/{employee_id}/roles")
async def assign_roles(employee_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.assign_roles(employee_id, body["role_codes"])
