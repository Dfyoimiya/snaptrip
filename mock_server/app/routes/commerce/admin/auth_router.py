"""Mock Server — B端 认证路由."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from fastapi import APIRouter

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.admin.admin import AdminLoginReq

from app import state

router = APIRouter(prefix="/auth")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.post("/login")
async def login(req: AdminLoginReq) -> Result[dict]:
    admins = _load("seed_admin_users.json")
    admin = next((a for a in admins if a.get("username") == req.username and a.get("password") == req.password), None)
    if not admin:
        return Result(code=ErrorCode.AUTH_WRONG_CREDENTIALS, message="用户名或密码错误")

    token = uuid.uuid4().hex
    refresh = uuid.uuid4().hex
    expires = int(time.time()) + 7200
    state._admin_sessions[token] = {"admin_id": admin["id"], "roles": admin.get("roles", []), "expires_at": expires}

    return Result(data={
        "token": token,
        "refresh_token": refresh,
        "expires_in": 7200,
        "admin_info": {
            "id": admin["id"],
            "username": admin["username"],
            "real_name": admin["real_name"],
            "roles": admin.get("roles", []),
            "permissions": admin.get("permissions", []),
        },
    })
