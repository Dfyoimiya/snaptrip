"""Mock Server — B端 商家审核管理."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.merchant.merchant import AuditReq, StatusReq

router = APIRouter(prefix="/merchants")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("")
async def list_merchants(
    audit_status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    merchants = _load("seed_merchants.json")
    if audit_status:
        merchants = [m for m in merchants if m.get("audit_status") == audit_status]
    total = len(merchants)
    start = (page - 1) * size
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": merchants[start:start + size]})


@router.put("/{merchant_id}/audit")
async def audit_merchant(merchant_id: str, req: AuditReq):
    merchants = _load("seed_merchants.json")
    m = next((m for m in merchants if m["id"] == merchant_id), None)
    if not m:
        return Result(code=ErrorCode.MERCH_NOT_FOUND, message="商家不存在")
    m["audit_status"] = req.status.value
    return Result(data=m)


@router.put("/{merchant_id}/status")
async def update_merchant_status(merchant_id: str, req: StatusReq):
    merchants = _load("seed_merchants.json")
    m = next((m for m in merchants if m["id"] == merchant_id), None)
    if not m:
        return Result(code=ErrorCode.MERCH_NOT_FOUND, message="商家不存在")
    m["status"] = req.status.value
    return Result(data=m)
