"""B端 商家管理路由."""

from fastapi import APIRouter, Body, Query, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/merchants")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("")
async def list_merchants(
    request: Request,
    audit_status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Result:
    return _svc(request).admin.list_merchants(
        {"audit_status": audit_status, "page": page, "size": size}
    )


@router.put("/{merchant_id}/audit")
async def audit_merchant(merchant_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.audit_merchant(
        merchant_id, body["status"], body.get("remark")
    )


@router.put("/{merchant_id}/status")
async def update_merchant_status(merchant_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.update_merchant_status(merchant_id, body["status"])
