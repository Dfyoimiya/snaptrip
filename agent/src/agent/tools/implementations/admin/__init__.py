"""Admin agent tools — analytics and B-end management tools.

Exports all 6 admin tools for the admin_analyst specialist node:
  - GetSalesReportTool
  - GetLowStockAlertTool
  - GetOrderTrendsTool
  - GetMemberInsightsTool
  - GenerateProductDescTool
  - AnalyzeCouponEffectTool
"""

from agent.tools.implementations.admin.get_sales_report import GetSalesReportTool
from agent.tools.implementations.admin.get_low_stock_alert import GetLowStockAlertTool
from agent.tools.implementations.admin.get_order_trends import GetOrderTrendsTool
from agent.tools.implementations.admin.get_member_insights import GetMemberInsightsTool
from agent.tools.implementations.admin.generate_product_desc import GenerateProductDescTool
from agent.tools.implementations.admin.analyze_coupon_effect import AnalyzeCouponEffectTool

__all__ = [
    "GetSalesReportTool",
    "GetLowStockAlertTool",
    "GetOrderTrendsTool",
    "GetMemberInsightsTool",
    "GenerateProductDescTool",
    "AnalyzeCouponEffectTool",
]
