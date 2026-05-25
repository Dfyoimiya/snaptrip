"""Mock Server — B端 分类管理."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.merchant.merchant import CategoryCreateReq, CategoryUpdateReq

from app import state

router = APIRouter(prefix="/categories")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("/tree")
async def get_tree():
    cats = _load("seed_categories.json")
    return Result(data=cats)


@router.post("")
async def create_category(req: CategoryCreateReq):
    cat = {"id": state.gen_uuid(), "name": req.name, "type": req.type, "parent_id": req.parent_id, "icon": req.icon, "sort_order": req.sort_order, "children": []}
    return Result(data=cat)


@router.put("/{category_id}")
async def update_category(category_id: str, req: CategoryUpdateReq):
    cats = _load("seed_categories.json")
    c = next((c for c in cats if c["id"] == category_id), None)
    if not c:
        return Result(code=ErrorCode.MERCH_NOT_FOUND, message="分类不存在")
    if req.name:
        c["name"] = req.name
    if req.icon:
        c["icon"] = req.icon
    if req.sort_order is not None:
        c["sort_order"] = req.sort_order
    return Result(data=c)


@router.delete("/{category_id}")
async def delete_category(category_id: str):
    cats = _load("seed_categories.json")
    children = [c for c in cats if c.get("parent_id") == category_id]
    if children:
        return Result(code=2003, message="该分类下有子分类，无法删除")
    return Result(message="已删除")
