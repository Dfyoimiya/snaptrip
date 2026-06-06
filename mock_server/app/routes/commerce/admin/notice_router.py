"""Mock Server — B端 公告管理."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter

from contracts.schemas.common import Result
from contracts.schemas.marketing.marketing import NoticeCreateReq

from app import state

router = APIRouter(prefix="/notices")
DATA = Path(__file__).parent.parent.parent.parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@router.get("")
async def list_notices():
    return Result(data=_load("seed_notices.json"))


@router.post("")
async def create_notice(req: NoticeCreateReq):
    n = {"id": state.gen_uuid(), "title": req.title, "content": req.content,
         "target_type": req.target_type, "status": "ACTIVE",
         "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    return Result(data=n)


@router.delete("/{notice_id}")
async def delete_notice(notice_id: str):
    return Result(message="已删除")
