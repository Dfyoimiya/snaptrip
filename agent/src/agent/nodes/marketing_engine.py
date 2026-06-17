"""Marketing Engine — coupons, flash deals, promotions."""

from __future__ import annotations

import logging
from typing import Any, cast

from agent.nodes.base import BaseSpecialist
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions ─────────────────────────────────────────────────────────

MARKETING_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_coupons",
            "description": "Get available coupons and discount codes. "
            "Returns active coupons with discount amount, minimum spend, "
            "validity dates, and applicable product categories. "
            "Can also retrieve the current user's claimed coupons by passing mode='mine'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["electronics", "clothing", "food", "home", "all"],
                        "description": "Filter coupons by product category (default: 'all')",
                    },
                    "min_discount": {
                        "type": "number",
                        "description": "Minimum discount amount to filter by",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["available", "mine"],
                        "description": "'available' for all coupons, 'mine' for user's claimed coupons (default: 'available')",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search products to find deals in specific categories. "
            "Useful for finding products that match a promotion or discount query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'flash sale', 'limited offer')",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["electronics", "clothing", "food", "home", "all"],
                        "description": "Product category filter",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results (default: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# ── System prompt ────────────────────────────────────────────────────────────

MARKETING_SYSTEM_PROMPT = """You are a marketing and promotions specialist for SnapTrip, an e-commerce platform.

Your job is to help users find the best deals, coupons, and promotions available.

Guidelines:
1. Use 'get_coupons' to find available discount codes. Filter by category if the user
   has a specific interest (electronics, clothing, food, home goods).
2. Use 'search_products' with queries like 'flash sale' or 'limited offer' to find
   promotional deals. Analyze results for savings and urgency.
3. Present deals and coupons in a clear, exciting way. Highlight the savings percentage
   and any urgency (e.g., "ends in 2 hours").
4. If there are no matching coupons, suggest checking deals via search or broader categories.
5. Never make up deals — only report what the tools return.
6. NEVER call a tool that you don't have defined.

When providing a final answer (without tool calls), structure your response as JSON:
{"answer": "Your coupon/deal recommendations here", "highlights": ["Best deal 1", "Discount amount"]}

Respond in the user's language. Be enthusiastic but honest.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


class MarketingEngineNode(BaseSpecialist):
    node_name = "marketing_engine"
    system_prompt = MARKETING_SYSTEM_PROMPT
    tools = MARKETING_TOOLS
    phase_name = "marketing_handling"
    temperature = 0.3


_instance = MarketingEngineNode()


async def marketing_engine_node(state: PlanState) -> dict:
    """Handle coupon/promotion queries. Calls get_coupons, search_products tools.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    return cast(dict, await _instance.execute(state))
