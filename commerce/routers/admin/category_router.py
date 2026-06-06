"""B端 分类管理路由."""

from fastapi import APIRouter, Body, Request
from contracts.schemas.common import Result

router = APIRouter(prefix="/categories")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.get("/tree")
async def get_category_tree(request: Request) -> Result:
    return _svc(request).admin.get_category_tree()


@router.post("")
async def create_category(body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.create_category(body)


@router.put("/{category_id}")
async def update_category(category_id: str, body: dict = Body(...), request: Request = None) -> Result:
    return _svc(request).admin.update_category(category_id, body)


@router.delete("/{category_id}")
async def delete_category(category_id: str, request: Request) -> Result:
    return _svc(request).admin.delete_category(category_id)
