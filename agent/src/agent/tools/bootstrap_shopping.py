"""Bootstrap — register all shopping guide tools into ToolRegistry.

Build and populate the ToolRegistry with shopping guide (read-only) tool implementations.

Usage:
    registry = build_shopping_guide_registry()
    harness = ToolHarness(registry=registry)
"""

from agent.tools.registry.registry import ToolRegistry
from agent.tools.implementations.compare_products import CompareProductsTool
from agent.tools.implementations.get_category_tree import GetCategoryTreeTool
from agent.tools.implementations.get_coupons import GetCouponsTool
from agent.tools.implementations.get_home_feed import GetHomeFeedTool
from agent.tools.implementations.get_price_history import GetPriceHistoryTool
from agent.tools.implementations.get_product_detail import GetProductDetailTool
from agent.tools.implementations.get_recommendations import GetRecommendationsTool
from agent.tools.implementations.search_products import SearchProductsTool


def build_shopping_guide_registry() -> ToolRegistry:
    """Build and register all shopping guide tools (8 read-only tools).

    Returns:
        ToolRegistry with all shopping guide tool instances registered
    """
    registry = ToolRegistry()
    registry.register(SearchProductsTool())
    registry.register(GetProductDetailTool())
    registry.register(GetRecommendationsTool())
    registry.register(GetHomeFeedTool())
    registry.register(GetCouponsTool())
    registry.register(CompareProductsTool())
    registry.register(GetCategoryTreeTool())
    registry.register(GetPriceHistoryTool())
    return registry
