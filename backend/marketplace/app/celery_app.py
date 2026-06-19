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
from snaptrip_shared.core.config import settings

celery_app = Celery(
    "snaptrip",
    broker=settings.effective_redis_url,
    backend=settings.effective_redis_url,
    include=["agent.tasks.plan_tasks", "app.tasks.cf_tasks", "app.tasks.coupon_tasks", "app.tasks.sla_tasks"],
)

celery_app.conf.update(
    task_default_queue="agent",
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
    # 定时任务
    beat_schedule={
        # 协同过滤模型训练: 每 6 小时
        "train_cf_model": {
            "task": "train_cf_model",
            "schedule": 6 * 60 * 60,  # 6 hours
            "options": {"queue": "agent"},
        },
        # SLA 监控: 每 60 秒检查超时工单
        "cs_sla_monitor": {
            "task": "check_sla_deadlines",
            "schedule": 60.0,
            "options": {"queue": "agent"},
        },
        # 坐席心跳清理: 每 120 秒
        "cs_agent_cleanup": {
            "task": "cleanup_stale_agents",
            "schedule": 120.0,
            "options": {"queue": "agent"},
        },
        # 优惠券自动过期: 每 60 秒
        "auto_expire_coupons": {
            "task": "auto_expire_coupons",
            "schedule": 60.0,
            "options": {"queue": "agent"},
        },
    },
)
