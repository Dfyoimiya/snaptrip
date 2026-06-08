"""Admin Analyst — analytics queries for B-end admin users.

Handles: sales reports, low stock alerts, order trends, member insights,
product description generation, coupon analysis.
"""

from __future__ import annotations

import logging
from typing import Any

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

ADMIN_SYSTEM_PROMPT = """You are an admin analytics assistant for SnapTrip, a travel e-commerce platform.

Your job is to help B-end administrators analyze business data and generate operational insights.

Capabilities:
1. **Sales Reports** — Use 'get_sales_report' to fetch dashboard metrics: revenue, orders, returns, status breakdown.
2. **Low Stock Alerts** — Use 'get_low_stock_alert' to identify products below inventory threshold.
3. **Order Trends** — Use 'get_order_trends' to analyze order patterns over time windows.
4. **Member Insights** — Use 'get_member_insights' for member statistics and activity data.
5. **Product Descriptions** — Use 'generate_product_desc' to create SEO-friendly product copy.
6. **Coupon Analysis** — Use 'analyze_coupon_effect' to measure coupon performance and usage rates.

Guidelines:
1. When the admin asks about sales or dashboard metrics, call 'get_sales_report'.
2. When they ask about inventory or stock alerts, call 'get_low_stock_alert'.
3. When they ask about order patterns or trends, call 'get_order_trends'.
4. When they ask about members or users, call 'get_member_insights'.
5. When they ask for product descriptions or SEO copy, call 'generate_product_desc'.
6. When they ask about coupon performance, call 'analyze_coupon_effect'.
7. Summarize results clearly with numbers, trends, and actionable recommendations.
8. Present data in a structured, easy-to-scan format appropriate for business users.
9. If no results are found or there are errors, be transparent and suggest next steps.
10. NEVER call a tool that you don't have defined.

Respond in the user's language. Be data-driven and professional.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


async def admin_analyst_node(state: PlanState) -> dict:
    """Handle admin analytics queries. Calls admin tools.

    On first turn: sends user query + system prompt to LLM with admin tool definitions.
    On subsequent turns (after tool results): LLM processes tool output and either
    calls more tools or returns a final answer.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    from agent.graph import _runtime

    adapter = _runtime.llm_adapter if _runtime else None
    if not adapter:
        logger.error("admin_analyst: LLM adapter unavailable")
        return {"phase": "error", "status": "llm_unavailable"}

    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)

    if retry_count > 3:
        logger.warning("admin_analyst: max retries exceeded, forcing synthesize")
        return {"phase": "admin_analytics", "status": "max_retries"}

    # Build messages: system prompt + accumulated conversation
    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": ADMIN_SYSTEM_PROMPT},
    ]
    # Convert LangChain messages to OpenAI dict format
    for msg in messages:
        if hasattr(msg, "type"):
            role = msg.type
            content = msg.content or ""
            role_map = {"human": "user", "ai": "assistant", "tool": "tool"}
            api_role = role_map.get(role, role)
            entry: dict[str, Any] = {"role": api_role, "content": content}
            # Include tool_calls if present on assistant messages
            if role == "ai":
                tcs = getattr(msg, "tool_calls", None) or []
                if tcs:
                    from agent.utils import normalize_tool_calls_for_api

                    entry["tool_calls"] = normalize_tool_calls_for_api(tcs)
            # Include tool_call_id on tool messages
            if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            llm_messages.append(entry)
        elif isinstance(msg, dict):
            llm_messages.append(msg)

    try:
        response = await adapter.chat(
            messages=llm_messages,
            tools=ADMIN_TOOLS,
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("admin_analyst: LLM call failed")
        return {"phase": "error", "status": "llm_error"}

    return {
        "messages": [response],
        "phase": "admin_analytics",
        "current_agent": "admin_analyst",
        "retry_count": retry_count + 1,
    }
