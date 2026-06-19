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

from fastapi import APIRouter, Depends, Header, Request
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
            from snaptrip_shared.core.security import verify_token

            token = authorization.removeprefix("Bearer ").strip()
            payload = verify_token(token)
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
        # ── view 行为：当天重复浏览同一商品 → 更新时间，不新增记录 ──
        if event.behavior_type == "view" and user_id and event.item_id:
            from sqlalchemy import func as sa_func, update as sa_update

            result = await db.execute(
                sa_update(UmsMemberBehavior)
                .where(
                    UmsMemberBehavior.user_id == user_id,
                    UmsMemberBehavior.item_id == UUID(event.item_id),
                    UmsMemberBehavior.behavior_type == "view",
                    UmsMemberBehavior.created_at >= sa_func.date_trunc("day", sa_func.now()),
                )
                .values(created_at=sa_func.now())
            )
            if result.rowcount and result.rowcount > 0:
                continue  # 已更新时间, 跳过新增

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


# ── 查询接口 ──


class BehaviorItemResponse(BaseModel):
    """浏览历史条目"""

    id: str
    behavior_type: str
    item_id: str | None = None
    item_type: str | None = None
    created_at: str | None = None
    # 关联的商品快照
    product_name: str | None = None
    product_pic: str | None = None
    product_price: float | None = None


class BehaviorListResponse(BaseModel):
    """浏览历史分页响应"""

    items: list[BehaviorItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SearchHistoryItem(BaseModel):
    """搜索历史条目"""

    keyword: str
    count: int
    last_searched_at: str | None = None


@router.get("", summary="查询用户行为历史")
async def list_behaviors(
    behavior_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    authorization: Annotated[str | None, Header()] = None,
):
    """查询当前用户的行为历史（浏览/搜索/加购/收藏）。

    支持按 behavior_type 过滤: view / search / add_cart / purchase / favorite。
    返回关联的商品信息（名称/图片/价格）。
    """
    from uuid import UUID as _UUID

    from sqlalchemy import desc, func, select as sa_select, text

    # ── 解析用户 ──
    user_id: _UUID | None = None
    if authorization:
        try:
            from snaptrip_shared.core.security import verify_token

            token = authorization.removeprefix("Bearer ").strip()
            payload = verify_token(token)
            user_id = _UUID(payload.get("sub", ""))
        except Exception:
            pass

    if user_id is None:
        return success({"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0})

    # ── 查询行为 ──
    base = sa_select(UmsMemberBehavior).where(UmsMemberBehavior.user_id == user_id)
    count_q = sa_select(func.count(UmsMemberBehavior.id)).where(UmsMemberBehavior.user_id == user_id)

    if behavior_type:
        base = base.where(UmsMemberBehavior.behavior_type == behavior_type)
        count_q = count_q.where(UmsMemberBehavior.behavior_type == behavior_type)

    result = await db.execute(count_q)
    total = result.scalar() or 0

    result = await db.execute(
        base.order_by(desc(UmsMemberBehavior.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    behaviors = result.scalars().all()

    # ── 批量获取关联商品信息 ──
    product_ids = [b.item_id for b in behaviors if b.item_id and b.item_type == "product"]
    product_map: dict[_UUID, dict] = {}
    if product_ids:
        from app.models.product.product import PmsProduct

        result = await db.execute(sa_select(PmsProduct).where(PmsProduct.id.in_(product_ids)))
        for p in result.scalars().all():
            product_map[p.id] = {"name": p.name, "pic": p.default_pic, "price": float(p.price) if p.price else None}

    items = []
    for b in behaviors:
        prod = product_map.get(b.item_id, {}) if b.item_id else {}
        items.append(
            BehaviorItemResponse(
                id=str(b.id),
                behavior_type=b.behavior_type,
                item_id=str(b.item_id) if b.item_id else None,
                item_type=b.item_type,
                created_at=b.created_at.isoformat() if b.created_at else None,
                product_name=prod.get("name"),
                product_pic=prod.get("pic"),
                product_price=prod.get("price"),
            )
        )

    total_pages = max((total + page_size - 1) // page_size, 0)
    return success(
        BehaviorListResponse(
            items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
        ).model_dump()
    )


@router.get("/search-history", summary="查询用户搜索历史")
async def list_search_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    authorization: Annotated[str | None, Header()] = None,
):
    """查询当前用户的搜索历史 —— 按最新时间排序的去重关键词列表。"""
    from uuid import UUID as _UUID

    from sqlalchemy import desc, func, select as sa_select

    user_id: _UUID | None = None
    if authorization:
        try:
            from snaptrip_shared.core.security import verify_token

            token = authorization.removeprefix("Bearer ").strip()
            payload = verify_token(token)
            user_id = _UUID(payload.get("sub", ""))
        except Exception:
            pass

    if user_id is None:
        return success({"items": []})

    # 去重关键词，按最近搜索时间排序
    result = await db.execute(
        sa_select(
            UmsMemberSearchLog.keyword,
            func.count(UmsMemberSearchLog.id).label("cnt"),
            func.max(UmsMemberSearchLog.created_at).label("last_at"),
        )
        .where(UmsMemberSearchLog.user_id == user_id)
        .group_by(UmsMemberSearchLog.keyword)
        .order_by(desc("last_at"))
        .limit(limit)
    )
    rows = result.all()
    items = [
        SearchHistoryItem(
            keyword=row.keyword,
            count=row.cnt,
            last_searched_at=row.last_at.isoformat() if row.last_at else None,
        )
        for row in rows
    ]
    return success({"items": [i.model_dump() for i in items]})


@router.delete("", summary="清空/批量删除用户行为历史")
async def clear_behaviors(
    behavior_type: str | None = None,
    ids: str | None = None,
    db: AsyncSession = Depends(get_db),
    authorization: Annotated[str | None, Header()] = None,
):
    """清空或批量删除当前用户的行为历史。

    - behavior_type: 按类型过滤删除 (如 view)
    - ids: 逗号分隔的行为记录 ID 列表，精确删除指定记录
    """
    from uuid import UUID as _UUID

    from sqlalchemy import delete as sa_delete

    user_id: _UUID | None = None
    if authorization:
        try:
            from snaptrip_shared.core.security import verify_token

            token = authorization.removeprefix("Bearer ").strip()
            payload = verify_token(token)
            user_id = _UUID(payload.get("sub", ""))
        except Exception:
            pass

    if user_id is None:
        return success({"deleted": 0, "message": "未登录"})

    stmt = sa_delete(UmsMemberBehavior).where(UmsMemberBehavior.user_id == user_id)
    if ids:
        id_list = [UUID(i.strip()) for i in ids.split(",") if i.strip()]
        if id_list:
            stmt = stmt.where(UmsMemberBehavior.id.in_(id_list))
    elif behavior_type:
        stmt = stmt.where(UmsMemberBehavior.behavior_type == behavior_type)

    result = await db.execute(stmt)
    await db.commit()
    return success({"deleted": result.rowcount, "message": "已删除"})
