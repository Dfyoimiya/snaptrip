"""Admin Analyst — analytics queries for B-end admin users.

Handles: sales reports, low stock alerts, order trends, member insights,
product description generation, coupon analysis.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.nodes.base import BaseSpecialist
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions (OpenAI function-calling format) ────────────────────────

ADMIN_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_report",
            "description": "Get sales report: today's revenue, today's orders, "
            "pending returns, and order status breakdown for the dashboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to report (1=today, 7=week)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_stock_alert",
            "description": "Get list of products with low stock (below threshold). "
            "Returns product name, SKU, current stock, and alert severity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "integer",
                        "description": "Stock threshold (default 20)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_trends",
            "description": "Get order trends: recent orders, status distribution, "
            "and total amounts over a configurable time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze (default 7)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_member_insights",
            "description": "Get member insights: total members, recent registrations, "
            "and member activity for the B-end dashboard.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_product_desc",
            "description": "Generate SEO-friendly product descriptions using templates. "
            "Produces 3 description suggestions and keyword list based on "
            "product name, category, features, and style preference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Product name",
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category (e.g., hotel, flight, tour, gear)",
                    },
                    "features": {
                        "type": "string",
                        "description": "Key features, comma-separated",
                    },
                    "style": {
                        "type": "string",
                        "enum": ["professional", "casual", "marketing"],
                        "description": "Writing style (default: 'professional')",
                    },
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_coupon_effect",
            "description": "Analyze coupon effectiveness: usage count, conversion rate, "
            "and discount totals. Works for a specific coupon or all coupons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coupon_id": {
                        "type": "string",
                        "description": "Specific coupon ID, or omit for all coupons",
                    },
                },
            },
        },
    },
]

# ── System prompt ────────────────────────────────────────────────────────────

ADMIN_SYSTEM_PROMPT = """You are a READ-ONLY admin analytics assistant for SnapTrip, a travel e-commerce platform.

Your job is to help B-end administrators ANALYZE business data. You CANNOT create, modify, or manage
any accounts, products, or orders. All your tools are analytical only.

Capabilities (READ-ONLY):
1. **Sales Reports** — Use 'get_sales_report' to fetch dashboard metrics: revenue, orders, returns, status breakdown.
2. **Low Stock Alerts** — Use 'get_low_stock_alert' to identify products below inventory threshold.
3. **Order Trends** — Use 'get_order_trends' to analyze order patterns over time windows.
4. **Member Insights** — Use 'get_member_insights' to check member statistics: total members, new registrations today, recent member signups, member activity. This answers questions like "有没有新会员", "新增会员", "会员增长情况", "会员数据".
5. **Product Descriptions** — Use 'generate_product_desc' to create SEO-friendly product copy.
6. **Coupon Analysis** — Use 'analyze_coupon_effect' to measure coupon performance and usage rates.

Guidelines:
1. When asked about sales or dashboard → call 'get_sales_report'.
2. When asked about inventory or stock → call 'get_low_stock_alert'.
3. When asked about orders or trends → call 'get_order_trends'.
4. When asked about members, users, new signups, registration → call 'get_member_insights'.
5. When asked for product copy or SEO → call 'generate_product_desc'.
6. When asked about coupon performance → call 'analyze_coupon_effect'.
7. ALWAYS call the relevant tool FIRST before giving an answer. Never guess or fabricate data.
8. Summarize results clearly with numbers, trends, and actionable recommendations.
9. If no results or errors → be transparent and suggest next steps.
10. NEVER call a tool that is not in the list above. You have NO account management tools.
11. NEVER claim you can "activate", "deactivate", "manage", "create", or "delete" anything — you CANNOT.

When providing a final answer (without tool calls), structure your response as JSON:
{"answer": "Your comprehensive analysis text here", "highlights": ["Key metric 1", "Key metric 2", "Recommendation"]}

Respond in the user's language. Be data-driven and professional.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


class AdminAnalystNode(BaseSpecialist):
    node_name = "admin_analyst"
    system_prompt = ADMIN_SYSTEM_PROMPT
    tools = ADMIN_TOOLS
    phase_name = "admin_analytics"
    temperature = 0.3


_admin_instance = AdminAnalystNode()


async def admin_analyst_node(state: PlanState) -> dict:
    """Handle admin analytics queries. Calls admin tools.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    return await _admin_instance.execute(state)
