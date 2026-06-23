"""
Shared Redis Pub/Sub helpers for portal and admin customer-service modules.

Extracted from app/api/portal/customer_service.py to eliminate duplication
across portal and admin chat endpoints.

Author: SnapTrip Team
Date: 2026-06-23
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import suppress

from fastapi import Request

logger = logging.getLogger(__name__)


def get_redis():
    """Create an async Redis client from configured Redis URL.

    Returns:
        aioredis.Redis instance or None if Redis is unavailable.
    """
    try:
        import redis.asyncio as aioredis
        from snaptrip_shared.core.config import settings

        return aioredis.from_url(settings.effective_redis_url)
    except Exception:
        logger.warning("Failed to create Redis client", exc_info=True)
        return None


async def publish_message(
    ticket_id: str,
    msg_id: str,
    sender_type: str,
    sender_id: str | None,
    content: str,
    content_type: str,
    created_at: str,
) -> None:
    """Publish a chat message to the ticket's Redis Pub/Sub channel (best-effort).

    This is a fire-and-forget operation. Callers should wrap with
    ``asyncio.create_task()`` to avoid blocking the request path.

    Args:
        ticket_id: The ticket UUID as a string.
        msg_id: The message UUID as a string.
        sender_type: "user" or "agent".
        sender_id: The sender's UUID as a string or None.
        content: Message body text.
        content_type: "text" or "image" etc.
        created_at: ISO-8601 timestamp string.
    """
    redis = get_redis()
    if not redis:
        return
    try:
        payload = json.dumps(
            {
                "id": msg_id,
                "ticket_id": ticket_id,
                "sender_type": sender_type,
                "sender_id": sender_id,
                "content": content,
                "content_type": content_type,
                "created_at": created_at,
            }
        )
        await redis.publish(f"ticket:{ticket_id}:messages", payload)
    except Exception:
        logger.warning("Failed to publish message to Redis", exc_info=True)
    finally:
        with suppress(Exception):
            await redis.close()


async def publish_ticket_event(event: str, ticket_id: str, status: str) -> None:
    """Publish a ticket lifecycle event to the B-end notification channel (best-effort).

    Publishes to ``cs:ticket:new`` so admin dashboards receive real-time
    notifications about new/updated tickets.

    Callers should wrap with ``asyncio.create_task()`` for fire-and-forget.

    Args:
        event: Event type, e.g. "ticket_created".
        ticket_id: The ticket UUID as a string.
        status: The ticket status, e.g. "open".
    """
    redis = get_redis()
    if not redis:
        return
    try:
        await redis.publish(
            "cs:ticket:new",
            json.dumps({"event": event, "ticket_id": ticket_id, "status": status}),
        )
    except Exception:
        logger.warning("Failed to publish ticket event to Redis", exc_info=True)
    finally:
        with suppress(Exception):
            await redis.close()


async def publish_admin_notification(recipient_id: str, payload: dict) -> None:
    """向指定管理员的通知 SSE 频道发布业务通知。"""
    redis = get_redis()
    if not redis:
        return
    try:
        await redis.publish(
            f"cs:agent:{recipient_id}:notify",
            json.dumps(payload, default=str),
        )
    except Exception:
        logger.warning("Failed to publish admin notification", exc_info=True)
    finally:
        with suppress(Exception):
            await redis.close()


async def message_stream(
    ticket_id: uuid.UUID,
    request: Request,
) -> AsyncGenerator[dict, None]:
    """SSE async generator that yields new messages from a ticket's Redis channel.

    Used by ``EventSourceResponse`` to stream real-time chat messages to
    the client. The generator exits cleanly when the client disconnects.

    Args:
        ticket_id: The ticket UUID.
        request: FastAPI Request (used to detect client disconnect).

    Yields:
        SSE-formatted dicts with "event" and "data" keys.
    """
    redis = get_redis()
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


async def notification_stream(
    recipient_id: uuid.UUID,
    request: Request,
) -> AsyncGenerator[dict, None]:
    """SSE async generator for admin agent notifications via Redis Pub/Sub.

    Used by ``EventSourceResponse`` to stream real-time notifications to
    the admin dashboard. The generator exits cleanly when the client disconnects.

    Args:
        recipient_id: The admin agent's UUID.
        request: FastAPI Request (used to detect client disconnect).

    Yields:
        SSE-formatted dicts with "event" and "data" keys.
    """
    redis = get_redis()
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


__all__ = [
    "get_redis",
    "message_stream",
    "notification_stream",
    "publish_admin_notification",
    "publish_message",
    "publish_ticket_event",
]
