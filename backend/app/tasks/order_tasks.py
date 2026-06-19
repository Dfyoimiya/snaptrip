"""
【Celery 定时任务 - 订单超时取消 + 自动确认收货】

知识点速查:
  - Celery Beat: 定时调度器, 配合 crontab 表达式定期执行
  - 为什么不用 APScheduler? Celery 已有成熟的分布式任务调度，无需引入新依赖

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from celery import shared_task
from snaptrip_shared.core.logging import get_logger

logger = get_logger(__name__)


@shared_task(name="auto_cancel_expired_orders", max_retries=1)
def auto_cancel_expired_orders() -> dict:
    """
    自动取消超时未支付订单。

    Celery Beat 配置 (每分钟执行):
      CELERY_BEAT_SCHEDULE = {
          "auto-cancel-every-minute": {
              "task": "auto_cancel_expired_orders",
              "schedule": 60.0,
          },
      }
    """
    import asyncio
    from datetime import UTC, datetime, timedelta

    async def _run():
        from snaptrip_shared.db.session import async_engine
        from sqlalchemy import select, update

        from app.core.config import commerce_settings
        from app.models.order.order import OmsOrder, OmsOrderItem, OmsOrderOperateLog
        from app.models.product.sku import PmsSku
        from app.schemas.order import OrderStatus

        try:
            await async_engine.dispose()
        except RuntimeError:
            pass  # 旧事件循环已关闭，连接无法清理，安全忽略

        timeout_minutes = commerce_settings.ORDER_AUTO_CANCEL_MINUTES
        deadline = datetime.now(UTC) - timedelta(minutes=timeout_minutes)

        async with _get_session() as session:
            # 查超时待付款订单
            result = await session.execute(
                select(OmsOrder)
                .where(
                    OmsOrder.status == OrderStatus.PENDING_PAYMENT,
                    OmsOrder.created_at < deadline,
                )
                .limit(100)
            )
            orders = result.scalars().all()

            cancelled = 0
            for order in orders:
                order.status = OrderStatus.CLOSED

                # 释放锁定库存
                items_result = await session.execute(select(OmsOrderItem).where(OmsOrderItem.order_id == order.id))
                for item in items_result.scalars().all():
                    await session.execute(
                        update(PmsSku)
                        .where(PmsSku.id == item.sku_id)
                        .values(lock_stock=PmsSku.lock_stock - item.quantity)
                    )

                session.add(
                    OmsOrderOperateLog(
                        order_id=order.id,
                        operate_man="system",
                        order_status_before=OrderStatus.PENDING_PAYMENT,
                        order_status_after=OrderStatus.CLOSED,
                        note=f"超时未支付自动取消 (>{timeout_minutes}分钟)",
                    )
                )
                cancelled += 1

            await session.commit()
            if cancelled:
                logger.info("auto_cancel_done", cancelled=cancelled, deadline=str(deadline))
            return {"cancelled": cancelled}

    return asyncio.run(_run())


@shared_task(name="auto_confirm_receipt_orders", max_retries=1)
def auto_confirm_receipt_orders() -> dict:
    """
    自动确认收货 + 自动完成订单。

    - 发货超过 auto_confirm_day 天的订单 → 自动确认收货 (DELIVERED → RECEIVED)
    - 收货超过 auto_confirm_day 天的订单 → 自动完成 (RECEIVED → COMPLETED)

    时效优先级: order.auto_confirm_day (per-order) > ORDER_AUTO_CONFIRM_DAYS / ORDER_AUTO_COMPLETE_DAYS (global).

    Celery Beat 配置 (每天凌晨2点执行):
      CELERY_BEAT_SCHEDULE = {
          "auto-confirm-receipt-daily": {
              "task": "auto_confirm_receipt_orders",
              "schedule": crontab(hour=2, minute=0),
          },
      }
    """
    import asyncio
    from datetime import UTC, datetime, timedelta

    async def _run():
        from snaptrip_shared.db.session import async_engine
        from sqlalchemy import select

        from app.core.config import commerce_settings
        from app.models.order.order import OmsOrder, OmsOrderOperateLog
        from app.schemas.order import OrderStatus

        try:
            await async_engine.dispose()
        except RuntimeError:
            pass  # 旧事件循环已关闭，连接无法清理，安全忽略

        default_confirm_days = commerce_settings.ORDER_AUTO_CONFIRM_DAYS
        default_complete_days = commerce_settings.ORDER_AUTO_COMPLETE_DAYS
        now = datetime.now(UTC)

        async with _get_session() as session:
            # ── 第一遍: 自动确认收货 (DELIVERED → RECEIVED) ──
            # Use a wide deadline (default) for the query, then filter per-order
            confirm_cutoff = now - timedelta(days=default_confirm_days)
            result = await session.execute(
                select(OmsOrder)
                .where(
                    OmsOrder.status == OrderStatus.DELIVERED,
                    OmsOrder.delivery_time < confirm_cutoff,
                    OmsOrder.confirm_status == 0,
                )
                .limit(500)
            )
            orders = result.scalars().all()

            confirmed = 0
            for order in orders:
                # Per-order auto_confirm_day takes precedence over global default
                per_order_days = order.auto_confirm_day if order.auto_confirm_day else default_confirm_days
                if order.delivery_time and order.delivery_time + timedelta(days=per_order_days) > now:
                    continue  # Not yet due for this specific order

                order.status = OrderStatus.RECEIVED
                order.confirm_status = 1
                session.add(
                    OmsOrderOperateLog(
                        order_id=order.id,
                        operate_man="system",
                        order_status_before=OrderStatus.DELIVERED,
                        order_status_after=OrderStatus.RECEIVED,
                        note=f"超{per_order_days}天自动确认收货",
                    )
                )
                confirmed += 1

            # ── 第二遍: 自动完成订单 (RECEIVED → COMPLETED) ──
            complete_cutoff = now - timedelta(days=default_complete_days)
            result = await session.execute(
                select(OmsOrder)
                .where(
                    OmsOrder.status == OrderStatus.RECEIVED,
                    OmsOrder.confirm_status == 1,
                    OmsOrder.updated_at < complete_cutoff,
                )
                .limit(500)
            )
            completed_orders = result.scalars().all()

            completed = 0
            for order in completed_orders:
                # Per-order auto_confirm_day also governs the auto-complete window
                per_order_days = order.auto_confirm_day if order.auto_confirm_day else default_complete_days
                if order.updated_at and order.updated_at + timedelta(days=per_order_days) > now:
                    continue

                order.status = OrderStatus.COMPLETED
                session.add(
                    OmsOrderOperateLog(
                        order_id=order.id,
                        operate_man="system",
                        order_status_before=OrderStatus.RECEIVED,
                        order_status_after=OrderStatus.COMPLETED,
                        note=f"超{per_order_days}天自动完成",
                    )
                )
                completed += 1

            await session.commit()
            if confirmed or completed:
                logger.info(
                    "auto_confirm_and_complete_done",
                    confirmed=confirmed,
                    completed=completed,
                )
            return {"confirmed": confirmed, "completed": completed}

    return asyncio.run(_run())


def _get_session():
    """获取异步会话 —— Celery 同步任务中创建独立事件循环"""
    from snaptrip_shared.db.session import AsyncSessionLocal

    return AsyncSessionLocal()
