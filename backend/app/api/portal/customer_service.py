"""
【前台商城 - 客服 API】— /api/v1/portal/cs

C2B 智能客服 Agent 后端支持：
  - 退货资格校验 / 提交退货申请
  - 退款进度查询 / 物流查询
  - 投诉校验 / 工单创建
  - 补偿优惠券发放
  - 工单聊天消息 / SSE 实时流

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from agent.services.agent import AgentService
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from snaptrip_shared.core.response import APIServiceError, success
from snaptrip_shared.db.session import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.models.member.cs_session import CsSessionSummary
from app.models.order.cs_message import CsConversationMessage
from app.models.order.order import OmsOrder
from app.models.order.return_apply import OmsReturnApply
from app.models.order.support_ticket import OmsSupportTicket
from app.models.promotion.coupon import SmsCoupon
from app.schemas.cs_admin import CsMessageListResponse, CsMessageRequest, CsMessageResponse
from app.schemas.customer_service import (
    CompensationRequest,
    CompensationResponse,
    ComplaintValidationResponse,
    CreateTicketRequest,
    CsHistoryResponse,
    LogisticsResponse,
    RefundStatusResponse,
    ReturnEligibilityResponse,
    ReturnSubmitRequest,
    ReturnSubmitResponse,
    SessionSummaryRequest,
    SessionSummaryResponse,
    TicketResponse,
)
from marketplace.app.core.security import get_current_user
from marketplace.app.models.users import User

router = APIRouter(prefix="/portal/cs", tags=["Portal - 客服"])

# ── 退货政策常量 ──────────────────────────────────────────────────────────

RETURN_POLICY_MAX_DAYS = 15
RETURNABLE_STATUSES = {2, 3}  # 已发货 / 已收货


def _order_status_text(status_code: int) -> str:
    """订单状态码 → 可读文本"""
    mapping = {
        0: "待付款",
        1: "已付款",
        2: "已发货",
        3: "已收货",
        4: "已完成",
        5: "已关闭",
        6: "已取消",
        7: "已退款",
    }
    return mapping.get(status_code, f"未知({status_code})")


# ════════════════════════════════════════════════════════════════════════════
#  退货资格校验
# ════════════════════════════════════════════════════════════════════════════


@router.get("/orders/{order_id}/return-eligibility", summary="校验退货资格")
async def check_return_eligibility(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """检查订单是否满足退货条件：状态 + 时间窗口"""
    result = await db.execute(select(OmsOrder).where(OmsOrder.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        return success(
            ReturnEligibilityResponse(
                eligible=False,
                reason="订单不存在",
                order_status=-1,
                order_status_text="不存在",
                days_since_delivery=None,
                policy_max_days=RETURN_POLICY_MAX_DAYS,
            ).model_dump()
        )

    if hasattr(order, "member_id") and str(order.member_id) != str(current_user.id):
        return success(
            ReturnEligibilityResponse(
                eligible=False,
                reason="订单不属于当前用户",
                order_status=order.status if hasattr(order, "status") else -1,
                order_status_text=_order_status_text(order.status if hasattr(order, "status") else -1),
                days_since_delivery=None,
                policy_max_days=RETURN_POLICY_MAX_DAYS,
            ).model_dump()
        )

    order_status = order.status if hasattr(order, "status") else -1

    if order_status not in RETURNABLE_STATUSES:
        return success(
            ReturnEligibilityResponse(
                eligible=False,
                reason=f"订单状态为'{_order_status_text(order_status)}'，不支持退货",
                order_status=order_status,
                order_status_text=_order_status_text(order_status),
                days_since_delivery=None,
                policy_max_days=RETURN_POLICY_MAX_DAYS,
            ).model_dump()
        )

    # Check time window: delivered_at + RETURN_POLICY_MAX_DAYS
    days_since = None
    if hasattr(order, "delivery_time") and order.delivery_time:
        days_since = (datetime.now(UTC) - order.delivery_time).days
    elif hasattr(order, "receive_time") and order.receive_time:
        days_since = (datetime.now(UTC) - order.receive_time).days
    elif hasattr(order, "updated_at"):
        days_since = (datetime.now(UTC) - order.updated_at).days

    if days_since is not None and days_since > RETURN_POLICY_MAX_DAYS:
        return success(
            ReturnEligibilityResponse(
                eligible=False,
                reason=f"已超过{RETURN_POLICY_MAX_DAYS}天退货期限（当前{days_since}天）",
                order_status=order_status,
                order_status_text=_order_status_text(order_status),
                days_since_delivery=days_since,
                policy_max_days=RETURN_POLICY_MAX_DAYS,
            ).model_dump()
        )

    return success(
        ReturnEligibilityResponse(
            eligible=True,
            reason=None,
            order_status=order_status,
            order_status_text=_order_status_text(order_status),
            days_since_delivery=days_since,
            policy_max_days=RETURN_POLICY_MAX_DAYS,
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  提交退货申请
# ════════════════════════════════════════════════════════════════════════════


@router.post("/orders/{order_id}/return", summary="提交退货申请", status_code=201)
async def submit_return_request(
    order_id: uuid.UUID,
    data: ReturnSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建退货申请记录"""
    # Validate order
    result = await db.execute(select(OmsOrder).where(OmsOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # Check for existing return
    existing = await db.execute(select(OmsReturnApply).where(OmsReturnApply.order_id == order_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该订单已有退货申请")

    return_apply = OmsReturnApply(
        order_id=order_id,
        product_id=uuid.uuid4(),  # placeholder — real impl would pull from order items
        order_sn=str(getattr(order, "order_sn", "")),
        member_username=getattr(current_user, "email", ""),
        return_amount=Decimal(str(getattr(order, "pay_amount", 0) or 0)),
        product_name="订单退货",
        reason=data.reason,
        description=data.description,
        product_count=data.product_count,
        status=0,  # 待处理
    )
    db.add(return_apply)
    await db.commit()
    await db.refresh(return_apply)

    return success(
        ReturnSubmitResponse(
            return_id=return_apply.id,
            order_id=order_id,
            status=0,
            return_amount=return_apply.return_amount,
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  退款进度查询
# ════════════════════════════════════════════════════════════════════════════


@router.get("/orders/{order_id}/refund-status", summary="查询退款进度")
async def query_refund_status(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询订单的退货/退款进度"""
    result = await db.execute(select(OmsReturnApply).where(OmsReturnApply.order_id == order_id))
    return_apply = result.scalar_one_or_none()

    if not return_apply:
        return success(
            RefundStatusResponse(
                order_id=order_id,
                has_return_request=False,
                return_status_text="未提交退货申请",
            ).model_dump()
        )

    status_map = {0: "待处理", 1: "已退货", 2: "已拒绝", 3: "已退款"}
    return success(
        RefundStatusResponse(
            return_id=return_apply.id,
            order_id=order_id,
            has_return_request=True,
            return_status=return_apply.status,
            return_status_text=status_map.get(return_apply.status, "未知"),
            refund_amount=return_apply.return_amount,
            applied_at=return_apply.created_at,
            handled_at=return_apply.handle_time,
            handle_note=return_apply.handle_note,
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  工单管理
# ════════════════════════════════════════════════════════════════════════════


@router.post("/tickets", summary="创建客服工单", status_code=201)
async def create_support_ticket(
    data: CreateTicketRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建工单升级到人工坐席"""
    ticket = OmsSupportTicket(
        order_id=data.order_id,
        member_id=current_user.id,
        type=data.type,
        status="open",
        priority=data.priority,
        title=data.title,
        description=data.description,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return success(TicketResponse.model_validate(ticket).model_dump())


@router.get("/tickets/{ticket_id}", summary="查询工单状态")
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询工单处理进度"""
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.member_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该工单")

    return success(TicketResponse.model_validate(ticket).model_dump())


# ════════════════════════════════════════════════════════════════════════════
#  补偿优惠券
# ════════════════════════════════════════════════════════════════════════════


@router.post("/compensate", summary="发放补偿优惠券", status_code=201)
async def issue_compensation_coupon(
    data: CompensationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """为客服补偿场景发放优惠券"""
    now = datetime.now(UTC)
    coupon = SmsCoupon(
        type=0,  # 全场券
        name=f"客服补偿券 ¥{data.amount}",
        amount=data.amount,
        min_point=Decimal("0.01"),
        platform=0,
        publish_count=1,
        use_count=0,
        receive_count=0,
        per_limit=1,
        enable_time=now,
        expire_time=now + timedelta(days=30),
        note=f"客服补偿: {data.reason}",
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)

    return success(
        CompensationResponse(
            coupon_id=coupon.id,
            amount=data.amount,
            reason=data.reason,
            message=f"已发放 ¥{data.amount} 补偿优惠券，30天内有效",
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  物流查询
# ════════════════════════════════════════════════════════════════════════════


@router.get("/orders/{order_id}/logistics", summary="查询物流信息")
async def check_logistics(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询订单物流信息 —— 当前为基础版本，生产环境对接快递鸟/菜鸟"""
    result = await db.execute(select(OmsOrder).where(OmsOrder.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    order_status = order.status if hasattr(order, "status") else -1
    return success(
        LogisticsResponse(
            order_id=order_id,
            order_status=order_status,
            order_status_text=_order_status_text(order_status),
            tracking_number=getattr(order, "delivery_sn", None) or None,
            carrier=None,
            estimated_delivery=None,
            delivered_at=getattr(order, "receive_time", None) or None,
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  投诉校验
# ════════════════════════════════════════════════════════════════════════════


@router.get("/orders/{order_id}/validate-complaint", summary="校验投诉合理性")
async def validate_order_complaint(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """校验用户投诉是否合理（订单存在、归属正确、状态允许）"""
    result = await db.execute(select(OmsOrder).where(OmsOrder.id == order_id))
    order = result.scalar_one_or_none()

    order_exists = order is not None
    order_belongs_to_user = (
        order_exists and hasattr(order, "member_id") and str(order.member_id) == str(current_user.id)
    )
    order_status_ok = (
        order_belongs_to_user
        and hasattr(order, "status")
        and order.status not in (5, 6, 7)  # not closed/cancelled/refunded
    )

    # Check previous complaints against this order
    prev_count = 0
    if order_exists:
        count_result = await db.execute(
            select(OmsSupportTicket).where(
                OmsSupportTicket.order_id == order_id,
                OmsSupportTicket.type == "complaint",
            )
        )
        prev_count = len(count_result.scalars().all())

    valid = order_exists and order_belongs_to_user and order_status_ok

    if not order_exists:
        suggested = "订单不存在，请核实订单号"
    elif not order_belongs_to_user:
        suggested = "订单不属于当前用户"
    elif not order_status_ok:
        suggested = "该订单已关闭/取消/退款，无法投诉"
    else:
        suggested = "投诉合理，建议引导用户提交退货申请或创建工单"

    return success(
        ComplaintValidationResponse(
            valid=valid,
            order_exists=order_exists,
            order_belongs_to_user=order_belongs_to_user,
            order_status_ok=order_status_ok,
            previous_complaints=prev_count,
            suggested_action=suggested,
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  会话记忆 (Phase 3 — 长期记忆管理)
# ════════════════════════════════════════════════════════════════════════════


@router.post("/sessions/summarize", summary="保存客服会话摘要", status_code=201)
async def save_session_summary(
    data: SessionSummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将 LLM 压缩的会话摘要持久化到 PG + 写入 Redis 缓存。

    Agent 在会话结束时调用此端点保存长期记忆。
    """
    import uuid as _uuid

    summary = CsSessionSummary(
        session_id=data.session_id,
        user_id=current_user.id,
        intent=data.intent,
        summary_text=data.summary_text,
        resolution_status=data.resolution_status,
        satisfaction_score=data.satisfaction_score,
        ticket_id=_uuid.UUID(data.ticket_id) if data.ticket_id else None,
        order_id=_uuid.UUID(data.order_id) if data.order_id else None,
        conversation_turns=data.conversation_turns,
        tools_called=data.tools_called,
        key_entities=data.key_entities,
        emotion_trajectory=data.emotion_trajectory,
    )
    db.add(summary)
    await db.commit()
    await db.refresh(summary)

    return success(
        SessionSummaryResponse(
            id=str(summary.id),
            session_id=summary.session_id,
            intent=summary.intent,
            summary_text=summary.summary_text,
            resolution_status=summary.resolution_status,
            satisfaction_score=summary.satisfaction_score,
            ticket_id=str(summary.ticket_id) if summary.ticket_id else None,
            order_id=str(summary.order_id) if summary.order_id else None,
            conversation_turns=summary.conversation_turns,
            tools_called=summary.tools_called,
            emotion_trajectory=summary.emotion_trajectory,
            created_at=summary.created_at.isoformat() if summary.created_at else "",
        ).model_dump()
    )


@router.get("/sessions/history", summary="查询用户客服历史")
async def get_cs_history(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户最近的客服会话摘要列表（从 PG 查询）。"""
    from sqlalchemy import desc

    result = await db.execute(
        select(CsSessionSummary)
        .where(CsSessionSummary.user_id == current_user.id)
        .order_by(desc(CsSessionSummary.created_at))
        .limit(limit)
    )
    summaries = result.scalars().all()

    sessions = [
        SessionSummaryResponse(
            id=str(s.id),
            session_id=s.session_id,
            intent=s.intent,
            summary_text=s.summary_text,
            resolution_status=s.resolution_status,
            satisfaction_score=s.satisfaction_score,
            ticket_id=str(s.ticket_id) if s.ticket_id else None,
            order_id=str(s.order_id) if s.order_id else None,
            conversation_turns=s.conversation_turns,
            tools_called=s.tools_called,
            emotion_trajectory=s.emotion_trajectory,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in summaries
    ]

    return success(
        CsHistoryResponse(
            user_id=str(current_user.id),
            sessions=sessions,
        ).model_dump()
    )


@router.get("/sessions/{session_id}", summary="查询指定会话摘要")
async def get_session_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定会话的摘要（用于恢复上下文）。"""
    result = await db.execute(select(CsSessionSummary).where(CsSessionSummary.session_id == session_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="会话摘要不存在")

    return success(
        SessionSummaryResponse(
            id=str(s.id),
            session_id=s.session_id,
            intent=s.intent,
            summary_text=s.summary_text,
            resolution_status=s.resolution_status,
            satisfaction_score=s.satisfaction_score,
            ticket_id=str(s.ticket_id) if s.ticket_id else None,
            order_id=str(s.order_id) if s.order_id else None,
            conversation_turns=s.conversation_turns,
            tools_called=s.tools_called,
            emotion_trajectory=s.emotion_trajectory,
            created_at=s.created_at.isoformat() if s.created_at else "",
        ).model_dump()
    )


# ════════════════════════════════════════════════════════════════════════════
#  工单聊天 (Phase 4 — 用户侧)
# ════════════════════════════════════════════════════════════════════════════


@router.get("/tickets/{ticket_id}/messages", summary="获取工单聊天历史（用户侧）")
async def get_ticket_messages_portal(
    ticket_id: uuid.UUID,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户获取工单聊天消息历史"""
    # Verify ticket belongs to user
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.member_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该工单")

    q = (
        select(CsConversationMessage)
        .where(CsConversationMessage.ticket_id == ticket_id)
        .order_by(CsConversationMessage.created_at.asc())
        .limit(limit)
    )
    result = await db.execute(q)
    messages = result.scalars().all()

    return success(
        CsMessageListResponse(
            ticket_id=ticket_id,
            messages=[CsMessageResponse.model_validate(m).model_dump() for m in messages],
        ).model_dump()
    )


@router.post("/tickets/{ticket_id}/messages", summary="用户发送聊天消息")
async def send_message_portal(
    ticket_id: uuid.UUID,
    data: CsMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户向工单发送聊天消息，通过 Redis Pub/Sub 推送给坐席"""
    # Verify ticket
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.member_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作该工单")

    msg = CsConversationMessage(
        ticket_id=ticket_id,
        sender_type="user",
        sender_id=current_user.id,
        content=data.content,
        content_type=data.content_type,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Publish to Redis for real-time delivery
    _portal_publish_message(str(ticket_id), msg)

    return success(CsMessageResponse.model_validate(msg).model_dump())


@router.get("/chat/{ticket_id}", summary="SSE 订阅工单消息流（用户侧）")
async def stream_ticket_portal(
    ticket_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE 端点 — 用户端订阅工单实时消息"""
    # Verify access
    result = await db.execute(select(OmsSupportTicket).where(OmsSupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.member_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看")

    return EventSourceResponse(_portal_message_stream(ticket_id, request))


# ═══ Portal CS Agent Chat ═══


class CsChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    session_id: str = Field("default", description="会话标识符")


class CsChatResponse(BaseModel):
    reply: str
    intent: str = ""
    data: dict | None = None


def _build_cs_state(req: CsChatRequest, user_id: str, auth_token: str = "") -> dict:
    """Build initial PlanState for portal CS agent chat.

    The auth_token (JWT from browser) is stored in working_memory so
    tool_node can inject it into the tool execution context.
    """
    plan_id = str(uuid.uuid4())[:8]
    return {
        "plan_id": plan_id,
        "user_id": f"user_{user_id}",
        "session_id": req.session_id or "default",
        "status": "running",
        "messages": [HumanMessage(content=req.message)],
        "intent": "",  # supervisor will classify
        "current_agent": "",  # supervisor will set
        "working_memory": {"auth_token": auth_token},
    }


def _get_agent_service(request: Request) -> AgentService:
    """Resolve AgentService from app state or build fallback."""
    if not hasattr(request.app.state, "_agent_service") or request.app.state._agent_service is None:
        if hasattr(request.app.state, "plan_graph") and request.app.state.plan_graph is not None:
            request.app.state._agent_service = AgentService(request.app.state.plan_graph)
        else:
            import asyncio

            from agent.graph import build_graph as _build

            request.app.state._agent_service = AgentService(asyncio.run(_build()))
    return request.app.state._agent_service


@router.post("/chat", summary="Portal AI 客服对话")
async def portal_cs_chat(
    req: CsChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Portal customer service AI chat endpoint.

    Routes through the LangGraph agent pipeline. The supervisor classifies
    the intent (cs_after_sales/cs_complaint/cs_inquiry) and routes to the
    customer_service specialist node which has 14 tools for order queries,
    returns/refunds, logistics, complaints, tickets, compensation, etc.
    """
    try:
        service = _get_agent_service(request)

        # Extract JWT from incoming request for passthrough to tools
        auth_header = request.headers.get("Authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

        initial_state = _build_cs_state(req, user_id=str(current_user.id), auth_token=auth_token)
        plan_id = initial_state["plan_id"]

        result = await service.invoke(initial_state, plan_id)

        # Extract the final synthesized message
        messages = result.get("messages", [])
        reply = ""
        intent = result.get("intent", "")

        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "ai":
                content = getattr(msg, "content", "")
                if content:
                    reply = str(content)
                    break
            elif isinstance(msg, dict) and msg.get("role") == "assistant":
                content = msg.get("content", "")
                if content:
                    reply = str(content)
                    break

        if not reply:
            reply = "处理完成。如需进一步帮助，请随时联系在线客服。"

        data = {
            "phase": result.get("phase", ""),
            "status": result.get("status", "done"),
            "current_agent": result.get("current_agent", ""),
        }

        return success(CsChatResponse(reply=reply, intent=intent, data=data).model_dump())

    except APIServiceError:
        raise
    except Exception as e:
        raise APIServiceError(
            code=5001,
            message=f"Portal CS agent error: {str(e)}",
            status_code=500,
        ) from e


# ════════════════════════════════════════════════════════════════════════════
#  Redis Pub/Sub 辅助 (Portal)
# ════════════════════════════════════════════════════════════════════════════


def _get_redis():
    try:
        import redis.asyncio as aioredis
        from snaptrip_shared.core.config import settings

        return aioredis.from_url(settings.effective_redis_url)
    except Exception:
        return None


def _portal_publish_message(ticket_id: str, msg: CsConversationMessage) -> None:
    """Publish chat message to Redis (best-effort)."""
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


async def _portal_message_stream(
    ticket_id: uuid.UUID,
    request: Request,
) -> AsyncGenerator[dict, None]:
    redis = _get_redis()
    if not redis:
        yield {"event": "error", "data": json.dumps({"message": "Redis unavailable"})}
        return

    channel = f"ticket:{ticket_id}:messages"
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(channel)
        yield {"event": "connected", "data": json.dumps({"ticket_id": str(ticket_id)})}
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield {"event": "new_message", "data": message["data"]}
            if await request.is_disconnected():
                break
    finally:
        with suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await redis.close()
