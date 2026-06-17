"""Bootstrap — register all commerce + CS + admin tools into ToolRegistry.

Build and populate the ToolRegistry with all tool implementations.

Usage:
    registry = build_commerce_registry()   # C-end tools only (6 + 7 CS = 13)
    registry = build_admin_registry()      # B-end tools only (6)
    registry = build_full_registry()       # All tools (19)
    harness = ToolHarness(registry=registry)
"""

from agent.tools.registry.registry import ToolRegistry
from agent.tools.implementations.cancel_order import CancelOrderTool
from agent.tools.implementations.check_logistics import CheckLogisticsTool
from agent.tools.implementations.check_return_eligibility import CheckReturnEligibilityTool
from agent.tools.implementations.create_support_ticket import CreateSupportTicketTool
from agent.tools.implementations.get_coupons import GetCouponsTool
from agent.tools.implementations.get_product_detail import GetProductDetailTool
from agent.tools.implementations.issue_compensation_coupon import IssueCompensationCouponTool
from agent.tools.implementations.query_order import QueryOrderTool
from agent.tools.implementations.query_refund_status import QueryRefundStatusTool
from agent.tools.implementations.save_session_summary import SaveSessionSummaryTool
from agent.tools.implementations.search_knowledge import SearchKnowledgeTool
from agent.tools.implementations.search_products import SearchProductsTool
from agent.tools.implementations.submit_return_request import SubmitReturnRequestTool
from agent.tools.implementations.validate_order_complaint import ValidateOrderComplaintTool
from agent.tools.implementations.admin import (
    AnalyzeCouponEffectTool,
    GenerateProductDescTool,
    GetLowStockAlertTool,
    GetMemberInsightsTool,
    GetOrderTrendsTool,
    GetSalesReportTool,
)


def _register_cs_tools(registry: ToolRegistry) -> None:
    """Register all customer service tools (7)."""
    registry.register(CheckReturnEligibilityTool())
    registry.register(SubmitReturnRequestTool())
    registry.register(QueryRefundStatusTool())
    registry.register(CreateSupportTicketTool())
    registry.register(IssueCompensationCouponTool())
    registry.register(CheckLogisticsTool())
    registry.register(ValidateOrderComplaintTool())
    registry.register(SaveSessionSummaryTool())


def build_commerce_registry() -> ToolRegistry:
    """Build and register all commerce (C-end) tools including CS."""
    registry = ToolRegistry()
    registry.register(CancelOrderTool())
    registry.register(GetCouponsTool())
    registry.register(GetProductDetailTool())
    registry.register(QueryOrderTool())
    registry.register(SearchKnowledgeTool())
    registry.register(SearchProductsTool())
    _register_cs_tools(registry)
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
    """Build and register all commerce + CS + admin tools (19 total)."""
    registry = build_commerce_registry()
    admin_registry = build_admin_registry()
    for name in admin_registry.tool_names:
        registry.register(admin_registry.get(name))
    return registry


def build_registry() -> ToolRegistry:
    """Legacy alias — builds the combined (commerce + CS + admin) registry."""
    return build_full_registry()
