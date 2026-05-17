"""Celery 异步任务框架配置。

Broker: Redis
Result Backend: Redis
序列化: JSON

启动 Worker:
    celery -A app.celery_app worker --loglevel=info

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "snaptrip",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.plan_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.AGENT_TIMEOUT,
    task_soft_time_limit=int(settings.AGENT_TIMEOUT * 0.8),
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
)
