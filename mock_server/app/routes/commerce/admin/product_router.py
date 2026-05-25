"""Mock Server — B端 商品管理."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query

from contracts.schemas.common import Result
from contracts.schemas.errors import ErrorCode
from contracts.schemas.product.product import ProductCreateReq, ProductUpdateReq

from app import state

router = APIRouter(prefix="/products")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("")
async def list_products(
    merchant_id: str = Query(default=None),
    category_id: str = Query(default=None),
    keyword: str = Query(default=None),
    status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    products = _load("seed_products.json")
    if merchant_id:
        products = [p for p in products if p.get("merchant_id") == merchant_id]
    if category_id:
        products = [p for p in products if p.get("category_id") == category_id]
    if keyword:
        kw = keyword.lower()
        products = [p for p in products if kw in p["name"].lower()]
    if status:
        products = [p for p in products if p.get("status") == status]
    total = len(products)
    start = (page - 1) * size
    return Result(data={"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size), "list": products[start:start + size]})


@router.post("")
async def create_product(req: ProductCreateReq):
    pid = state.gen_uuid()
    prod = {"id": pid, "merchant_id": req.merchant_id, "category_id": req.category_id,
            "name": req.name, "description": req.description, "image": req.image,
            "images": req.images, "price": req.price, "original_price": req.original_price,
            "stock": req.stock, "sales": 0, "rating": 0.0, "status": "ON_SHELF",
            "has_specs": len(req.specs) > 0, "category_name": "",
            "specs": [{"spec_id": state.gen_uuid(), "spec_name": s.spec_name,
                       "values": [{"value_id": state.gen_uuid(), "value_name": v.value_name,
                                   "price_offset": v.price_offset, "stock": v.stock} for v in s.values]}
                      for s in req.specs],
            "flavors": [{"flavor_id": state.gen_uuid(), "flavor_name": f.flavor_name, "extra_price": f.extra_price}
                        for f in req.flavors]}
    return Result(data=prod)


@router.put("/{product_id}")
async def update_product(product_id: str, req: ProductUpdateReq):
    products = _load("seed_products.json")
    p = next((p for p in products if p["id"] == product_id), None)
    if not p:
        return Result(code=ErrorCode.PROD_NOT_FOUND, message="商品不存在")
    for field in ("name", "description", "image", "price", "original_price", "stock", "category_id"):
        val = getattr(req, field, None)
        if val is not None:
            p[field] = val
    return Result(data=p)


@router.put("/{product_id}/status")
async def toggle_status(product_id: str, body: dict):
    products = _load("seed_products.json")
    p = next((p for p in products if p["id"] == product_id), None)
    if not p:
        return Result(code=ErrorCode.PROD_NOT_FOUND, message="商品不存在")
    p["status"] = body.get("status", p["status"])
    return Result(data=None)


@router.put("/batch/status")
async def batch_status(body: dict):
    ids = body.get("ids", [])
    status = body.get("status", "")
    products = _load("seed_products.json")
    for p in products:
        if p["id"] in ids:
            p["status"] = status
    return Result(data=None)
