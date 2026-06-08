"""Bootstrap — register all commerce + admin tools into ToolRegistry.

Build and populate the ToolRegistry with all tool implementations.

Usage:
    registry = build_commerce_registry()   # C-end tools only (6)
    registry = build_admin_registry()      # B-end tools only (6)
    registry = build_full_registry()       # All tools (12)
    harness = ToolHarness(registry=registry)
"""

from agent.tools.registry.registry import ToolRegistry
from agent.tools.implementations.cancel_order import CancelOrderTool
from agent.tools.implementations.get_coupons import GetCouponsTool
from agent.tools.implementations.get_product_detail import GetProductDetailTool
from agent.tools.implementations.query_order import QueryOrderTool
from agent.tools.implementations.search_knowledge import SearchKnowledgeTool
from agent.tools.implementations.search_products import SearchProductsTool
from agent.tools.implementations.admin import (
    AnalyzeCouponEffectTool,
    GenerateProductDescTool,
    GetLowStockAlertTool,
    GetMemberInsightsTool,
    GetOrderTrendsTool,
    GetSalesReportTool,
)


def build_commerce_registry() -> ToolRegistry:
    """Build and register all commerce (C-end) tools."""
    registry = ToolRegistry()
    registry.register(CancelOrderTool())
    registry.register(GetCouponsTool())
    registry.register(GetProductDetailTool())
    registry.register(QueryOrderTool())
    registry.register(SearchKnowledgeTool())
    registry.register(SearchProductsTool())
    return registry


def build_admin_registry() -> ToolRegistry:
    """Build and register all admin (B-end) tools."""
    registry = ToolRegistry()
    registry.register(AnalyzeCouponEffectTool())
    registry.register(GenerateProductDescTool())
    registry.register(GetLowStockAlertTool())
    registry.register(GetMemberInsightsTool())
    registry.register(GetOrderTrendsTool())
    registry.register(GetSalesReportTool())
    return registry


def build_full_registry() -> ToolRegistry:
    """Build and register all commerce + admin tools (12 total)."""
    registry = build_commerce_registry()
    admin_registry = build_admin_registry()
    for name in admin_registry.tool_names:
        registry.register(admin_registry.get(name))
    return registry


def build_registry() -> ToolRegistry:
    """Legacy alias — builds the combined (commerce + admin) registry."""
    return build_full_registry()
