"""Mock Server — B端 轮播图管理."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query

from contracts.schemas.common import Result
from contracts.schemas.marketing.marketing import BannerCreateReq, BannerUpdateReq

from app import state

router = APIRouter(prefix="/banners")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("")
async def list_banners(position: str = Query(default=None)):
    banners = _load("seed_banners.json")
    if position:
        banners = [b for b in banners if b.get("position") == position]
    return Result(data=banners)


@router.post("")
async def create_banner(req: BannerCreateReq):
    b = {"id": state.gen_uuid(), "image_url": req.image_url, "link_type": req.link_type,
         "link_id": req.link_id, "sort_order": req.sort_order, "status": "ACTIVE"}
    return Result(data=b)


@router.put("/{banner_id}")
async def update_banner(banner_id: str, req: BannerUpdateReq):
    banners = _load("seed_banners.json")
    b = next((b for b in banners if b["id"] == banner_id), None)
    if b:
        for field in ("image_url", "link_type", "link_id", "sort_order", "status"):
            val = getattr(req, field, None)
            if val is not None:
                b[field] = val
    return Result(data=b)


@router.delete("/{banner_id}")
async def delete_banner(banner_id: str):
    return Result(message="已删除")
