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
        from sqlalchemy import select, update

        from app.core.config import commerce_settings
        from app.models.order.order import OmsOrder, OmsOrderItem, OmsOrderOperateLog
        from app.models.product.sku import PmsSku

        timeout_minutes = commerce_settings.ORDER_AUTO_CANCEL_MINUTES
        deadline = datetime.now(UTC) - timedelta(minutes=timeout_minutes)

        async with _get_session() as session:
            # 查超时待付款订单
            result = await session.execute(
                select(OmsOrder).where(
                    OmsOrder.status == 0,  # 待付款
                    OmsOrder.created_at < deadline,
                ).limit(100)
            )
            orders = result.scalars().all()

            cancelled = 0
            for order in orders:
                order.status = 5  # 已关闭

                # 释放锁定库存
                items_result = await session.execute(
                    select(OmsOrderItem).where(OmsOrderItem.order_id == order.id)
                )
                for item in items_result.scalars().all():
                    await session.execute(
                        update(PmsSku)
                        .where(PmsSku.id == item.sku_id)
                        .values(lock_stock=PmsSku.lock_stock - item.quantity)
                    )

                session.add(OmsOrderOperateLog(
                    order_id=order.id,
                    operate_man="system",
                    order_status_before=0,
                    order_status_after=5,
                    note=f"超时未支付自动取消 (>{timeout_minutes}分钟)",
                ))
                cancelled += 1

            await session.commit()
            if cancelled:
                logger.info("auto_cancel_done", cancelled=cancelled, deadline=str(deadline))
            return {"cancelled": cancelled}

    return asyncio.run(_run())


@shared_task(name="auto_confirm_receipt_orders", max_retries=1)
def auto_confirm_receipt_orders() -> dict:
    """
    自动确认收货 —— 发货超过 N 天自动确认。

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
        from sqlalchemy import select

        from app.core.config import commerce_settings
        from app.models.order.order import OmsOrder, OmsOrderOperateLog

        auto_confirm_days = commerce_settings.ORDER_AUTO_CONFIRM_DAYS
        deadline = datetime.now(UTC) - timedelta(days=auto_confirm_days)

        async with _get_session() as session:
            result = await session.execute(
                select(OmsOrder).where(
                    OmsOrder.status == 2,  # 已发货
                    OmsOrder.delivery_time < deadline,
                    OmsOrder.confirm_status == 0,
                ).limit(500)
            )
            orders = result.scalars().all()

            confirmed = 0
            for order in orders:
                order.status = 3  # 已收货
                order.confirm_status = 1
                session.add(OmsOrderOperateLog(
                    order_id=order.id,
                    operate_man="system",
                    order_status_before=2,
                    order_status_after=3,
                    note=f"超{auto_confirm_days}天自动确认收货",
                ))
                confirmed += 1

            await session.commit()
            if confirmed:
                logger.info("auto_confirm_done", confirmed=confirmed)
            return {"confirmed": confirmed}

    return asyncio.run(_run())


def _get_session():
    """获取异步会话 —— Celery 同步任务中创建独立事件循环"""
    from snaptrip_shared.db.session import AsyncSessionLocal
    return AsyncSessionLocal()
