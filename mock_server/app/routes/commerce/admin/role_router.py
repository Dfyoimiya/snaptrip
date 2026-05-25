"""Mock Server — B端 角色权限管理."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from contracts.schemas.common import Result
from contracts.schemas.admin.admin import RoleCreateReq, PermissionAssignReq

from app import state

router = APIRouter(prefix="/roles")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("")
async def list_roles():
    roles = _load("seed_roles.json")
    return Result(data=roles)


@router.post("")
async def create_role(req: RoleCreateReq):
    role = {"id": state.gen_uuid(), "role_code": req.role_code, "role_name": req.role_name, "description": req.description, "permission_codes": req.permission_codes}
    return Result(data=role)


@router.put("/{role_id}/permissions")
async def assign_permissions(role_id: str, req: PermissionAssignReq):
    return Result(data={"role_id": role_id, "permission_codes": req.permission_codes})


@router.get("/permissions/tree")
async def get_permission_tree():
    trees = [
        {"code": "dashboard", "name": "仪表盘", "children": [{"code": "dashboard:view", "name": "查看仪表盘", "children": []}]},
        {"code": "employee", "name": "员工管理", "children": [
            {"code": "employee:list", "name": "查看员工", "children": []},
            {"code": "employee:create", "name": "新增员工", "children": []},
            {"code": "employee:update", "name": "编辑员工", "children": []},
            {"code": "employee:delete", "name": "删除员工", "children": []},
            {"code": "employee:assign_role", "name": "分配角色", "children": []},
        ]},
        {"code": "merchant", "name": "商家管理", "children": [
            {"code": "merchant:list", "name": "查看商家", "children": []},
            {"code": "merchant:audit", "name": "审核商家", "children": []},
            {"code": "merchant:status", "name": "营业状态控制", "children": []},
        ]},
        {"code": "category", "name": "分类管理", "children": [
            {"code": "category:list", "name": "查看分类", "children": []},
            {"code": "category:create", "name": "新增分类", "children": []},
            {"code": "category:update", "name": "编辑分类", "children": []},
            {"code": "category:delete", "name": "删除分类", "children": []},
        ]},
        {"code": "product", "name": "商品管理", "children": [
            {"code": "product:list", "name": "查看商品", "children": []},
            {"code": "product:create", "name": "新增商品", "children": []},
            {"code": "product:update", "name": "编辑商品", "children": []},
            {"code": "product:status", "name": "上下架", "children": []},
        ]},
        {"code": "order", "name": "订单管理", "children": [
            {"code": "order:list", "name": "查看订单", "children": []},
            {"code": "order:status", "name": "状态流转", "children": []},
            {"code": "order:export", "name": "导出报表", "children": []},
        ]},
        {"code": "banner", "name": "轮播图", "children": [
            {"code": "banner:list", "name": "查看", "children": []},
            {"code": "banner:create", "name": "新增", "children": []},
            {"code": "banner:update", "name": "编辑", "children": []},
            {"code": "banner:delete", "name": "删除", "children": []},
        ]},
        {"code": "notice", "name": "公告管理", "children": [
            {"code": "notice:list", "name": "查看", "children": []},
            {"code": "notice:create", "name": "新增", "children": []},
            {"code": "notice:delete", "name": "删除", "children": []},
        ]},
        {"code": "stats", "name": "数据统计", "children": [
            {"code": "stats:revenue", "name": "营业额统计", "children": []},
            {"code": "stats:orders", "name": "订单统计", "children": []},
            {"code": "stats:users", "name": "用户统计", "children": []},
            {"code": "stats:ranking", "name": "商品排行", "children": []},
        ]},
        {"code": "upload", "name": "文件上传", "children": [{"code": "upload:image", "name": "上传图片", "children": []}]},
    ]
    return Result(data=trees)
