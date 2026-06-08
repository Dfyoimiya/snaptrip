"""
【后台管理 - 仪表盘 API】— /api/v1/admin/dashboard

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from snaptrip_shared.core.response import success
from marketplace.app.core.security import get_current_user
from snaptrip_shared.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - 仪表盘"])


@router.get("", summary="仪表盘聚合数据")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    返回管理后台首页所需的所有聚合数据:
      - today_orders: 今日订单数
      - today_revenue: 今日销售额(分)
      - today_revenue_display: 今日销售额格式化显示
      - pending_returns: 待处理退货数
      - new_members: 今日新增会员数
      - order_status_counts: 各状态订单数量
      - top_products: 商品销售排行 TOP5
      - week_days: 近7天每日标签
      - week_sales: 近7天每日销售额
      - latest_orders: 最新5条订单
    """
    today = date.today()
    week_start = today - timedelta(days=6)

    # TODO: 当 OrderService/ProductService/MemberService 提供对应的统计方法后，
    # 替换以下占位数据为真实的服务调用。

    # ── 占位数据：确保前端能端到端跑通 ──
    data = {
        "today_orders": 128,
        "today_revenue": 2568000,  # 分
        "today_revenue_display": "¥25,680",
        "pending_returns": 8,
        "new_members": 36,
        "order_status_counts": [
            {"label": "待付款", "count": 23, "type": "warning"},
            {"label": "待发货", "count": 45, "type": "primary"},
            {"label": "已发货", "count": 68, "type": "success"},
            {"label": "已完成", "count": 1256, "type": "info"},
            {"label": "退款中", "count": 8, "type": "danger"},
        ],
        "top_products": [
            {"name": "iPhone 15 Pro", "sales": 156, "amount": 1403844},
            {"name": "华为Mate60 Pro", "sales": 128, "amount": 895872},
            {"name": "戴森吹风机", "sales": 98, "amount": 322420},
            {"name": "AirPods Pro 2", "sales": 87, "amount": 139113},
            {"name": "索尼WH-1000XM5", "sales": 72, "amount": 215928},
        ],
        "week_days": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
        "week_sales": [18500, 22300, 19800, 25600, 31200, 28900, 25680],
        "latest_orders": [
            {"id": 1, "orderSn": "ORD20250602001", "member": "张三", "amount": 8999, "status": 1, "statusLabel": "待发货"},
            {"id": 2, "orderSn": "ORD20250602002", "member": "李四", "amount": 3290, "status": 2, "statusLabel": "已发货"},
            {"id": 3, "orderSn": "ORD20250602003", "member": "王五", "amount": 1599, "status": 0, "statusLabel": "待付款"},
            {"id": 4, "orderSn": "ORD20250602004", "member": "赵六", "amount": 2599, "status": 2, "statusLabel": "已发货"},
            {"id": 5, "orderSn": "ORD20250602005", "member": "钱七", "amount": 6999, "status": 1, "statusLabel": "待发货"},
        ],
    }

    # TODO: 真实实现示例 —— 当各 Service 具备统计方法后取消注释
    #
    # from app.services.order_service import OrderService
    # from app.services.product_service import ProductService
    # from app.services.member_service import MemberService
    #
    # order_svc = OrderService(db)
    # product_svc = ProductService(db)
    # member_svc = MemberService(db)
    #
    # data["today_orders"] = await order_svc.count_today()
    # data["today_revenue"] = await order_svc.revenue_today()
    # data["pending_returns"] = await order_svc.count_pending_returns()
    # data["new_members"] = await member_svc.count_new_today()
    # data["order_status_counts"] = await order_svc.status_counts()
    # data["top_products"] = await product_svc.top_by_sales(limit=5)
    # data["week_sales"] = await order_svc.revenue_daily_range(week_start, today)
    # data["latest_orders"] = await order_svc.latest(limit=5)

    return success(data)
