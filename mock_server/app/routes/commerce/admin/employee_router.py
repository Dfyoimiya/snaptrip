"""Mock Server — B端 员工管理."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, Query

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.admin.admin import EmployeeCreateReq, EmployeeUpdateReq, RoleAssignReq

from app import state

router = APIRouter(prefix="/employees")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("")
async def list_employees(page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100)):
    employees = _load("seed_admin_users.json")
    total = len(employees)
    start = (page - 1) * size
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": employees[start:start + size]})


@router.post("")
async def create_employee(req: EmployeeCreateReq):
    eid = state.gen_uuid()
    emp = {
        "id": eid, "username": req.username, "password": req.password,
        "real_name": req.real_name, "phone": req.phone,
        "avatar": None, "status": "ACTIVE",
        "roles": req.role_codes, "permissions": [],
        "created_at": "2024-06-01T10:00:00Z",
    }
    state._admin_users[eid] = emp
    return Result(data=emp)


@router.put("/{employee_id}")
async def update_employee(employee_id: str, req: EmployeeUpdateReq):
    emp = state._admin_users.get(employee_id)
    if not emp:
        return Result(code=ErrorCode.USER_TOKEN_INVALID, message="员工不存在")
    if req.real_name:
        emp["real_name"] = req.real_name
    if req.phone:
        emp["phone"] = req.phone
    if req.status:
        emp["status"] = req.status
    return Result(data=emp)


@router.delete("/{employee_id}")
async def delete_employee(employee_id: str):
    state._admin_users.pop(employee_id, None)
    return Result(message="已删除")


@router.put("/{employee_id}/roles")
async def assign_roles(employee_id: str, req: RoleAssignReq):
    emp = state._admin_users.get(employee_id)
    if emp:
        emp["roles"] = req.role_codes
    return Result(data=emp)
