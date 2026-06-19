"""
【后台管理 - 客服管理 API】— /api/v1/admin/cs

人工坐席后台：
  - 工单列表/详情/更新/指派/解决
  - 聊天消息收发 + SSE 实时流
  - 坐席状态管理
  - 通知列表/已读
  - 客服统计

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.rbac import require_admin_user
from app.models.infra.notification import CsNotification
from app.models.member.cs_agent import CsAgentStatus
from app.models.order.cs_message import CsConversationMessage
from app.models.order.support_ticket import OmsSupportTicket
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.cs_admin import (
    AgentStatusResponse,
    AgentStatusUpdate,
    CsMessageListResponse,
    CsMessageRequest,
    CsMessageResponse,
    CsStatsResponse,
    NotificationListResponse,
    NotificationResponse,
    TicketAssignRequest,
    TicketResolveRequest,
    TicketResponse,
    TicketUpdateRequest,
)

router = APIRouter(prefix="/admin/cs", tags=["Admin - 客服管理"])

# ── SLA 配置 ─────────────────────────────────────────────────────────────────

SLA_DEADLINES = {
    "critical": timedelta(minutes=15),
    "urgent": timedelta(hours=1),
    "normal": timedelta(hours=4),
}


def _compute_sla_deadline(priority: str) -> datetime | None:
    delta = SLA_DEADLINES.get(priority)
    return datetime.now(UTC) + delta if delta else None


# ════════════════════════════════════════════════════════════════════════════
#  工单管理
# ════════════════════════════════════════════════════════════════════════════


@router.get("/tickets", summary="工单分页列表")
async def list_tickets(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    type: str | None = Query(None),
    assigned_agent_id: UUID | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    """工单列表，支持按状态/优先级/类型/坐席/关键词筛选"""
    base = select(OmsSupportTicket)
    count_q = select(func.count(OmsSupportTicket.id))

    if status:
        base = base.where(OmsSupportTicket.status == status)
        count_q = count_q.where(OmsSupportTicket.status == status)
    if priority:
        base = base.where(OmsSupportTicket.priority == priority)
        count_q = count_q.where(OmsSupportTicket.priority == priority)
    if type:
        base = base.where(OmsSupportTicket.type == type)
        count_q = count_q.where(OmsSupportTicket.type == type)
    if assigned_agent_id:
        base = base.where(OmsSupportTicket.assigned_agent_id == assigned_agent_id)
        count_q = count_q.where(OmsSupportTicket.assigned_agent_id == assigned_agent_id)
    if keyword:
        like = f"%{keyword}%"
        base = base.where(OmsSupportTicket.title.ilike(like) | OmsSupportTicket.description.ilike(like))
        count_q = count_q.where(OmsSupportTicket.title.ilike(like) | OmsSupportTicket.description.ilike(like))

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    items_result = await db.execute(
        base.order_by(OmsSupportTicket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    tickets = items_result.scalars().all()

    return success(
        PaginatedResponse.of(
            items=[TicketResponse.model_validate(t).model_dump() for t in tickets],
            total=total,
            params=PaginationParams(page=page, page_size=page_size),
        ).model_dump()
    )


@router.get("/tickets/{ticket_id}", summary="工单详情")
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    """获取工单详情"""
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return success(TicketResponse.model_validate(ticket).model_dump())


@router.put("/tickets/{ticket_id}", summary="更新工单")
async def update_ticket(
    ticket_id: UUID,
    data: TicketUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_user),
):
    """更新工单状态/优先级/标签/处理结果"""
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    if data.status is not None:
        ticket.status = data.status
        if data.status == "resolved" or data.status == "closed":
            ticket.resolved_at = datetime.now(UTC)
    if data.priority is not None:
        ticket.priority = data.priority
        ticket.sla_deadline = _compute_sla_deadline(data.priority)
    if data.tags is not None:
        ticket.tags = data.tags
    if data.resolution is not None:
        ticket.resolution = data.resolution
    if data.satisfaction_score is not None:
        ticket.satisfaction_score = data.satisfaction_score

    ticket.updated_by = current_user.id
    await db.commit()
    await db.refresh(ticket)

    # Notify via Redis if available
    _publish_ticket_event("ticket_updated", str(ticket_id), ticket.status)

    return success(TicketResponse.model_validate(ticket).model_dump())


@router.post("/tickets/{ticket_id}/assign", summary="指派/认领工单")
async def assign_ticket(
    ticket_id: UUID,
    data: TicketAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_user),
):
    """指派坐席或认领工单"""
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    agent_id = data.agent_id
    if data.action == "claim":
        agent_id = current_user.id
    elif data.action == "unassign":
        agent_id = None

    ticket.assigned_agent_id = agent_id
    if agent_id and ticket.status == "open":
        ticket.status = "in_progress"
        if not ticket.first_response_at:
            ticket.first_response_at = datetime.now(UTC)
    elif not agent_id and ticket.status == "in_progress":
        ticket.status = "open"

    ticket.updated_by = current_user.id
    await db.commit()
    await db.refresh(ticket)

    # Create notification for assigned agent
    if agent_id:
        notif = CsNotification(
            recipient_id=agent_id,
            type="ticket_assigned",
            ticket_id=ticket_id,
            title=f"工单已指派: {ticket.title}",
        )
        db.add(notif)
        await db.commit()

    _publish_ticket_event("ticket_assigned", str(ticket_id), ticket.status)

    return success(TicketResponse.model_validate(ticket).model_dump())


@router.post("/tickets/{ticket_id}/resolve", summary="解决/关闭工单")
async def resolve_ticket(
    ticket_id: UUID,
    data: TicketResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_user),
):
    """解决工单，填写处理结果"""
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    ticket.status = "resolved"
    ticket.resolution = data.resolution
    ticket.resolved_at = datetime.now(UTC)
    if data.satisfaction_score is not None:
        ticket.satisfaction_score = data.satisfaction_score
    ticket.updated_by = current_user.id

    # Add system message
    sys_msg = CsConversationMessage(
        ticket_id=ticket_id,
        sender_type="system",
        content=f"工单已解决: {data.resolution}",
        content_type="system_event",
    )
    db.add(sys_msg)
    await db.commit()
    await db.refresh(ticket)

    _publish_ticket_event("ticket_resolved", str(ticket_id), "resolved")

    return success(TicketResponse.model_validate(ticket).model_dump())


# ════════════════════════════════════════════════════════════════════════════
#  聊天消息
# ════════════════════════════════════════════════════════════════════════════


@router.get("/tickets/{ticket_id}/messages", summary="获取聊天历史")
async def list_messages(
    ticket_id: UUID,
    limit: int = Query(50, le=200),
    before: UUID | None = Query(None, description="游标：获取此消息之前的历史"),
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    """获取工单聊天消息，支持游标分页"""
    q = select(CsConversationMessage).where(CsConversationMessage.ticket_id == ticket_id)
    if before:
        # Get messages created before this message
        ref = await db.execute(select(CsConversationMessage).where(CsConversationMessage.id == before))
        ref_msg = ref.scalar_one_or_none()
        if ref_msg:
            q = q.where(CsConversationMessage.created_at < ref_msg.created_at)

    q = q.order_by(CsConversationMessage.created_at.asc()).limit(limit)
    result = await db.execute(q)
    messages = result.scalars().all()

    return success(
        CsMessageListResponse(
            ticket_id=ticket_id,
            messages=[CsMessageResponse.model_validate(m).model_dump() for m in messages],
        ).model_dump()
    )


@router.post("/tickets/{ticket_id}/messages", summary="坐席发送消息")
async def send_message(
    ticket_id: UUID,
    data: CsMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_user),
):
    """坐席向工单发送聊天消息，通过 Redis Pub/Sub 推送给用户"""
    # Verify ticket exists
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # Update first_response_at on first agent message
    if not ticket.first_response_at:
        ticket.first_response_at = datetime.now(UTC)

    msg = CsConversationMessage(
        ticket_id=ticket_id,
        sender_type="agent",
        sender_id=current_user.id,
        content=data.content,
        content_type=data.content_type,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Publish to Redis for real-time delivery
    _publish_message(str(ticket_id), msg)

    return success(CsMessageResponse.model_validate(msg).model_dump())


@router.get("/tickets/{ticket_id}/stream", summary="SSE 订阅工单消息流")
async def stream_ticket_messages(
    ticket_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    """SSE 端点 — 坐席端订阅工单实时消息"""
    return EventSourceResponse(_message_stream(ticket_id, request, db))


# ════════════════════════════════════════════════════════════════════════════
#  坐席状态
# ════════════════════════════════════════════════════════════════════════════


@router.get("/agents", summary="在线坐席列表")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    """获取所有坐席状态"""
    from marketplace.app.models.users import User

    result = await db.execute(select(CsAgentStatus))
    statuses = result.scalars().all()

    # Resolve admin names
    agents = []
    for s in statuses:
        user_result = await db.execute(select(User).where(User.id == s.admin_id))
        user = user_result.scalar_one_or_none()
        agents.append(
            AgentStatusResponse(
                admin_id=s.admin_id,
                status=s.status,
                current_ticket_id=s.current_ticket_id,
                max_concurrent=s.max_concurrent,
                last_heartbeat=s.last_heartbeat,
                skills=s.skills,
                admin_name=user.email if user else None,
            ).model_dump()
        )

    return success(agents)


@router.put("/agents/me/status", summary="更新坐席状态")
async def update_agent_status(
    data: AgentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_user),
):
    """坐席更新自己的在线状态"""
    result = await db.execute(select(CsAgentStatus).where(CsAgentStatus.admin_id == current_user.id))
    agent_status = result.scalar_one_or_none()

    if agent_status:
        agent_status.status = data.status
        agent_status.current_ticket_id = data.current_ticket_id
        agent_status.last_heartbeat = datetime.now(UTC)
    else:
        # First time: create status record
        agent_status = CsAgentStatus(
            admin_id=current_user.id,
            status=data.status,
            current_ticket_id=data.current_ticket_id,
            last_heartbeat=datetime.now(UTC),
        )
        db.add(agent_status)

    await db.commit()
    await db.refresh(agent_status)

    return success(
        AgentStatusResponse(
            admin_id=agent_status.admin_id,
            status=agent_status.status,
            current_ticket_id=agent_status.current_ticket_id,
            max_concurrent=agent_status.max_concurrent,
            last_heartbeat=agent_status.last_heartbeat,
            skills=agent_status.skills,
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  通知
# ════════════════════════════════════════════════════════════════════════════


@router.get("/notifications", summary="通知列表")
async def list_notifications(
    is_read: bool | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_user),
):
    """获取当前坐席的通知列表"""
    q = select(CsNotification).where(CsNotification.recipient_id == current_user.id)
    if is_read is not None:
        q = q.where(CsNotification.is_read == is_read)

    q = q.order_by(CsNotification.created_at.desc()).limit(limit)
    result = await db.execute(q)
    notifications = result.scalars().all()

    # Count unread
    unread_result = await db.execute(
        select(func.count(CsNotification.id)).where(
            CsNotification.recipient_id == current_user.id,
            CsNotification.is_read == False,  # noqa: E712
        )
    )
    unread_count = unread_result.scalar() or 0
    total_result = await db.execute(
        select(func.count(CsNotification.id)).where(CsNotification.recipient_id == current_user.id)
    )
    total = total_result.scalar() or 0

    return success(
        NotificationListResponse(
            items=[NotificationResponse.model_validate(n).model_dump() for n in notifications],
            unread_count=unread_count,
            total=total,
        ).model_dump()
    )


@router.put("/notifications/{notification_id}/read", summary="标记通知已读")
async def mark_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_user),
):
    """标记指定通知为已读"""
    result = await db.execute(select(CsNotification).where(CsNotification.id == notification_id))
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="通知不存在")
    if notif.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")

    notif.is_read = True
    notif.read_at = datetime.now(UTC)
    await db.commit()

    return success(NotificationResponse.model_validate(notif).model_dump())


@router.put("/notifications/read-all", summary="全部已读")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_user),
):
    """标记当前坐席所有通知为已读"""
    await db.execute(
        text(
            "UPDATE cs_notifications SET is_read = true, read_at = now() WHERE recipient_id = :uid AND is_read = false"
        ),
        {"uid": current_user.id},
    )
    await db.commit()
    return success({"message": "ok"})


@router.get("/notifications/stream", summary="SSE 订阅通知流")
async def stream_notifications(
    request: Request,
    current_user=Depends(require_admin_user),
):
    """SSE 端点 — 坐席端订阅实时通知"""
    return EventSourceResponse(_notification_stream(current_user.id, request))


# ════════════════════════════════════════════════════════════════════════════
#  客服统计
# ════════════════════════════════════════════════════════════════════════════


@router.get("/stats", summary="客服统计")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _u=Depends(require_admin_user),
):
    """获取客服统计数据"""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total tickets
    total_result = await db.execute(select(func.count(OmsSupportTicket.id)))
    total = total_result.scalar() or 0

    # Open count
    open_result = await db.execute(select(func.count(OmsSupportTicket.id)).where(OmsSupportTicket.status == "open"))
    open_count = open_result.scalar() or 0

    # In progress
    ip_result = await db.execute(
        select(func.count(OmsSupportTicket.id)).where(OmsSupportTicket.status == "in_progress")
    )
    ip_count = ip_result.scalar() or 0

    # Resolved today
    resolved_result = await db.execute(
        select(func.count(OmsSupportTicket.id)).where(
            OmsSupportTicket.status.in_(["resolved", "closed"]),
            OmsSupportTicket.resolved_at >= today_start,
        )
    )
    resolved_today = resolved_result.scalar() or 0

    # SLA breach count
    sla_result = await db.execute(
        select(func.count(OmsSupportTicket.id)).where(
            OmsSupportTicket.sla_deadline.isnot(None),
            OmsSupportTicket.sla_deadline < now,
            OmsSupportTicket.status.in_(["open", "in_progress"]),
            OmsSupportTicket.first_response_at.is_(None),
        )
    )
    sla_breach = sla_result.scalar() or 0

    # Online agents
    agents_result = await db.execute(
        select(func.count(CsAgentStatus.id)).where(CsAgentStatus.status.in_(["online", "busy"]))
    )
    online_agents = agents_result.scalar() or 0

    # Average response time (approximate: first_response_at - created_at for resolved today)
    avg_result = await db.execute(
        select(func.avg(OmsSupportTicket.first_response_at - OmsSupportTicket.created_at)).where(
            OmsSupportTicket.first_response_at.isnot(None),
            OmsSupportTicket.resolved_at >= today_start,
        )
    )
    avg_raw = avg_result.scalar()
    avg_minutes = round(avg_raw.total_seconds() / 60, 1) if avg_raw else None

    return success(
        CsStatsResponse(
            total_tickets=total,
            open_count=open_count,
            in_progress_count=ip_count,
            resolved_today=resolved_today,
            avg_response_minutes=avg_minutes,
            sla_breach_count=sla_breach,
            online_agents=online_agents,
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  Redis Pub/Sub 辅助函数
# ════════════════════════════════════════════════════════════════════════════


def _get_redis():
    """Lazy import redis client from shared config."""
    try:
        import redis.asyncio as aioredis
        from snaptrip_shared.core.config import settings

        return aioredis.from_url(settings.effective_redis_url)
    except Exception:
        return None


def _publish_ticket_event(event: str, ticket_id: str, status: str) -> None:
    """Publish ticket event to Redis (best-effort)."""
    try:
        import asyncio

        async def _pub():
            redis = _get_redis()
            if redis:
                await redis.publish(
                    "cs:ticket:new",
                    json.dumps({"event": event, "ticket_id": ticket_id, "status": status}),
                )
                await redis.close()

        asyncio.create_task(_pub())
    except Exception:
        pass


def _publish_message(ticket_id: str, msg: CsConversationMessage) -> None:
    """Publish chat message to Redis Pub/Sub (best-effort)."""
    try:
        import asyncio

        async def _pub():
            redis = _get_redis()
            if redis:
                payload = json.dumps(
                    {
                        "id": str(msg.id),
                        "ticket_id": ticket_id,
                        "sender_type": msg.sender_type,
                        "sender_id": str(msg.sender_id) if msg.sender_id else None,
                        "content": msg.content,
                        "content_type": msg.content_type,
                        "created_at": msg.created_at.isoformat() if msg.created_at else "",
                    }
                )
                await redis.publish(f"ticket:{ticket_id}:messages", payload)
                await redis.close()

        asyncio.create_task(_pub())
    except Exception:
        pass


async def _message_stream(
    ticket_id: UUID,
    request: Request,
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    """SSE generator — streams chat messages for a ticket via Redis Pub/Sub."""
    redis = _get_redis()
    if not redis:
        yield {"event": "error", "data": json.dumps({"message": "Redis unavailable"})}
        return

    channel = f"ticket:{ticket_id}:messages"
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(channel)
        # Send initial connection event
        yield {"event": "connected", "data": json.dumps({"ticket_id": str(ticket_id)})}
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield {"event": "new_message", "data": message["data"]}
            # Check if client disconnected
            if await request.is_disconnected():
                break
    finally:
        with suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await redis.close()


async def _notification_stream(
    recipient_id: UUID,
    request: Request,
) -> AsyncGenerator[dict, None]:
    """SSE generator — streams notifications for an admin agent via Redis Pub/Sub."""
    redis = _get_redis()
    if not redis:
        yield {"event": "error", "data": json.dumps({"message": "Redis unavailable"})}
        return

    channel = f"cs:agent:{recipient_id}:notify"
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(channel)
        yield {"event": "connected", "data": json.dumps({"recipient": str(recipient_id)})}
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield {"event": "notification", "data": message["data"]}
            if await request.is_disconnected():
                break
    finally:
        with suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await redis.close()
