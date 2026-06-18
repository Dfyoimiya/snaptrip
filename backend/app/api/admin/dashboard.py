"""
【后台管理 - 仪表盘 API】— /api/v1/admin/dashboard

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from snaptrip_shared.core.response import success
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_admin_user
from app.services.member_service import MemberService
from app.services.order_service import OrderService
from app.services.product_service import ProductService

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - 仪表盘"])

# 中文星期映射
_WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


@router.get("", summary="仪表盘聚合数据")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin_user),
):
    """
    返回管理后台首页所需的所有聚合数据。
    """
    today = date.today()
    week_start = today - timedelta(days=6)

    order_svc = OrderService(db)
    product_svc = ProductService(db)
    member_svc = MemberService(db)

    today_orders = await order_svc.count_today()
    today_revenue = await order_svc.revenue_today()
    pending_returns = await order_svc.count_pending_returns()
    new_members = await member_svc.count_new_today()
    order_status_counts = await order_svc.status_counts()
    top_products = await product_svc.top_by_sales(limit=5)
    week_sales = await order_svc.revenue_daily_range(week_start, today)
    latest_orders = await order_svc.latest(limit=5)

    # 生成近7天中文标签
    week_days = []
    d = week_start
    while d <= today:
        week_days.append(_WEEKDAY_NAMES[d.weekday()])
        d += timedelta(days=1)

    return success(
        {
            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "today_revenue_display": f"¥{today_revenue:,}",
            "pending_returns": pending_returns,
            "new_members": new_members,
            "order_status_counts": order_status_counts,
            "top_products": top_products,
            "week_days": week_days,
            "week_sales": week_sales,
            "latest_orders": latest_orders,
        }
    )
