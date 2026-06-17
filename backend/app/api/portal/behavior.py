"""前台 - 用户行为追踪 API — /api/v1/portal/behaviors

接收前端埋点上报, 写入行为事件表和 Redis 滑动窗口。
轻量级 fire-and-forget, 不阻塞主请求。

注意:
  - 匿名用户通过 session_id 关联, 登录后关联 user_id
  - POST body 支持批量上报, 单次最多 50 条

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Request
from pydantic import BaseModel, Field
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member.behavior import UmsMemberBehavior, UmsMemberSearchLog
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/portal/behaviors", tags=["Portal - 行为追踪"])

MAX_BATCH_SIZE = 50


class BehaviorEvent(BaseModel):
    """单条行为事件"""
    behavior_type: str = Field(..., description="行为类型: view/search/add_cart/purchase/favorite")
    item_id: str | None = Field(None, description="关联对象ID")
    item_type: str | None = Field(None, description="对象类型: product/category/brand/coupon")
    metadata: dict | None = Field(None, description="扩展信息")


class BehaviorBatchRequest(BaseModel):
    """批量行为上报请求"""
    session_id: str = Field(..., min_length=1, max_length=64, description="会话ID")
    events: list[BehaviorEvent] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)


def _get_memory_service(request: Request) -> MemoryService:
    """从 app state 获取 MemoryService (由 lifespan 注入)。"""
    svc = request.app.state.memory
    if svc is None:
        raise RuntimeError("MemoryService not initialized")
    return svc


@router.post("", summary="批量上报用户行为")
async def track_behaviors(
    body: BehaviorBatchRequest,
    db: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(_get_memory_service),
    # 可选认证: 用户可能在请求头中携带 token
    authorization: Annotated[str | None, Header()] = None,
):
    """批量接收前端埋点事件。

    双写策略:
      1. PostgreSQL: 持久化存储 (UmsMemberBehavior)
      2. Redis Sorted Set: 实时滑动窗口 (供特征聚合查询)

    目前写 PG 为异步 fire-and-forget, 不等待 DB 写入完成。
    """
    # 尝试解析 user_id (可选)
    user_id: UUID | None = None
    if authorization:
        try:
            from marketplace.app.core.security import decode_access_token

            token = authorization.removeprefix("Bearer ").strip()
            payload = decode_access_token(token)
            user_id = UUID(payload.get("sub", ""))
        except Exception:
            pass

    now_ts = time.time()

    for event in body.events:
        # 1. 写 Redis 滑动窗口 (快速路径)
        try:
            item_id = event.item_id or "_"
            await memory.record_behavior(
                user_id=str(user_id) if user_id else body.session_id,
                behavior_type=event.behavior_type,
                item_id=item_id,
                metadata=event.metadata or {},
            )
        except Exception:
            pass  # Redis 写入失败不影响 PG 写入

        # 2. 写 PostgreSQL (持久化)
        if event.behavior_type == "search":
            # 搜索事件 -> 搜索日志表
            keyword_str = event.metadata.get("keyword", "") if event.metadata else ""
            search_log = UmsMemberSearchLog(
                user_id=user_id,
                session_id=body.session_id,
                keyword=keyword_str,
                filters=event.metadata.get("filters") if event.metadata else None,
                result_count=event.metadata.get("result_count") if event.metadata else None,
            )
            db.add(search_log)

            # 同步更新自动补全索引
            if keyword_str:
                try:
                    from app.services.autocomplete_service import AutocompleteService
                    autocomplete_svc = AutocompleteService(memory)
                    await autocomplete_svc.increment(keyword_str)
                except Exception:
                    pass  # 不影响主流程

        behavior = UmsMemberBehavior(
            user_id=user_id,
            session_id=body.session_id,
            behavior_type=event.behavior_type,
            item_id=UUID(event.item_id) if event.item_id else None,
            item_type=event.item_type,
            metadata_=event.metadata,
        )
        db.add(behavior)

    # Fire-and-forget: 不等待 commit 完成
    try:
        await db.commit()
    except Exception:
        await db.rollback()

    return success({"tracked": len(body.events)})
