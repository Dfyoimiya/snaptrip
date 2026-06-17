"""SLA 监控定时任务 — Celery Beat 周期调度

监控客服工单的 SLA 响应截止时间，超时后发送通知。

调度频率: 每 60 秒
清理频率: 每 120 秒 (离线坐席心跳清理)

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

from celery import shared_task
from snaptrip_shared.core.logging import get_logger

logger = get_logger(__name__)

# ── SLA 阈值 ──
SLA_DEADLINES = {
    "critical": timedelta(minutes=15),
    "urgent": timedelta(hours=1),
    "normal": timedelta(hours=4),
}


@shared_task(
    name="check_sla_deadlines",
    max_retries=1,
    default_retry_delay=30,
    soft_time_limit=55,
)
def check_sla_deadlines() -> dict:
    """扫描 open/in_progress 状态的工单，检查 SLA 是否超时。

    超时规则:
      - critical: 15 分钟内未首次响应 → sla_breach
      - urgent:   1 小时内未首次响应   → sla_breach
      - normal:   4 小时内未首次响应   → sla_breach
      - 即将超时 (80% 时间)          → sla_warning

    对超时工单:
      1. 写入 cs_notifications 通知指派坐席
      2. 发布 Redis Pub/Sub 实时告警
    """
    return asyncio.get_event_loop().run_until_complete(_check_sla())


async def _check_sla() -> dict:
    from snaptrip_shared.core.config import settings
    from snaptrip_shared.db.session import AsyncSessionLocal
    from sqlalchemy import select

    from app.models.infra.notification import CsNotification
    from app.models.order.support_ticket import OmsSupportTicket

    now = datetime.now(UTC)
    warned = 0
    breached = 0

    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.REDIS_URL)
    except Exception:
        redis = None

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OmsSupportTicket).where(
                OmsSupportTicket.status.in_(["open", "in_progress"]),
                OmsSupportTicket.first_response_at.is_(None),
            )
        )
        tickets = result.scalars().all()

        for ticket in tickets:
            deadline = SLA_DEADLINES.get(ticket.priority, SLA_DEADLINES["normal"])
            elapsed = now - ticket.created_at
            warning_threshold = deadline * 0.8

            if elapsed > deadline:
                # SLA breached
                breached += 1
                notif = CsNotification(
                    recipient_id=ticket.assigned_agent_id if ticket.assigned_agent_id
                    else ticket.created_by or ticket.id,  # fallback
                    type="sla_breach",
                    ticket_id=ticket.id,
                    title=f"SLA 超时: {ticket.title}",
                    body=f"工单 {ticket.id} 已超过 {ticket.priority} 级 SLA ({_format_td(deadline)})，"
                         f"当前耗时 {_format_td(elapsed)}",
                )
                db.add(notif)

                # Publish real-time alert
                if redis:
                    await redis.publish(
                        "cs:sla:warning",
                        json.dumps({
                            "type": "sla_breach",
                            "ticket_id": str(ticket.id),
                            "priority": ticket.priority,
                            "elapsed_minutes": int(elapsed.total_seconds() / 60),
                        }),
                    )

            elif elapsed > warning_threshold:
                # SLA warning (80% threshold)
                warned += 1
                if redis:
                    await redis.publish(
                        "cs:sla:warning",
                        json.dumps({
                            "type": "sla_warning",
                            "ticket_id": str(ticket.id),
                            "priority": ticket.priority,
                            "elapsed_minutes": int(elapsed.total_seconds() / 60),
                            "remaining_minutes": int((deadline - elapsed).total_seconds() / 60),
                        }),
                    )

        await db.commit()

    if redis:
        await redis.close()

    if warned or breached:
        logger.info("sla_check: warned=%d breached=%d", warned, breached)
    return {"warned": warned, "breached": breached}


@shared_task(
    name="cleanup_stale_agents",
    max_retries=0,
    soft_time_limit=30,
)
def cleanup_stale_agents() -> dict:
    """清理离线超时的坐席状态。

    超过 5 分钟没有心跳的坐席标记为 offline。
    """
    return asyncio.get_event_loop().run_until_complete(_cleanup_agents())


async def _cleanup_agents() -> dict:
    from snaptrip_shared.db.session import AsyncSessionLocal
    from sqlalchemy import update

    from app.models.member.cs_agent import CsAgentStatus

    now = datetime.now(UTC)
    stale_threshold = now - timedelta(minutes=5)
    cleaned = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(CsAgentStatus)
            .where(
                CsAgentStatus.status.in_(["online", "busy"]),
                CsAgentStatus.last_heartbeat < stale_threshold,
            )
            .values(status="offline", current_ticket_id=None)
        )
        cleaned = result.rowcount or 0
        await db.commit()

    if cleaned:
        logger.info("cleanup_stale_agents: %d agents marked offline", cleaned)
    return {"cleaned": cleaned}


def _format_td(td: timedelta) -> str:
    """Format timedelta as human-readable string."""
    total_minutes = int(td.total_seconds() / 60)
    if total_minutes >= 60:
        hours = total_minutes // 60
        mins = total_minutes % 60
        return f"{hours}小时{mins}分钟"
    return f"{total_minutes}分钟"
