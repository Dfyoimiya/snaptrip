"""
【优惠券定时任务】— 自动过期 + 其他周期作业

Author: SnapTrip Team
Date: 2026-06-18
"""

from __future__ import annotations

from datetime import UTC, datetime

from celery.utils.log import get_task_logger
from snaptrip_shared.db.session import AsyncSessionLocal

from marketplace.app.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    name="auto_expire_coupons",
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=60,
    time_limit=120,
)
def auto_expire_coupons() -> dict:
    """
    自动过期优惠券 —— 每分钟执行一次。

    将 use_status=0（未使用）且 expire_time < now() 的记录
    更新为 use_status=2（已过期）。
    """
    import asyncio

    return asyncio.run(_auto_expire_coupons_async())


async def _auto_expire_coupons_async() -> dict:
    from snaptrip_shared.db.session import async_engine
    from sqlalchemy import update

    from app.models.promotion.coupon import SmsCouponHistory

    try:
        await async_engine.dispose()  # 绑定到当前 event loop
    except RuntimeError:
        pass  # 旧事件循环已关闭，连接无法清理，安全忽略

    now = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        stmt = (
            update(SmsCouponHistory)
            .where(
                SmsCouponHistory.use_status == 0,
                SmsCouponHistory.expire_time < now,
            )
            .values(use_status=2)
        )
        result = await db.execute(stmt)
        affected = result.rowcount
        await db.commit()

        count = affected or 0
        logger.info("auto_expire_coupons: expired %d coupon histories", count)
        return {"expired_count": count}
