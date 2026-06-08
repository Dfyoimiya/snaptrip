"""Marketing Engine — coupons, flash deals, promotions."""

from __future__ import annotations

import logging
from typing import Any

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions ─────────────────────────────────────────────────────────

MARKETING_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_coupons",
            "description": "Get available coupons and discount codes for the user. "
                           "Returns active coupons with discount amount, minimum spend, "
                           "validity dates, and applicable product categories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["hotel", "flight", "tour", "package", "all"],
                        "description": "Filter coupons by product category (default: 'all')",
                    },
                    "min_discount": {
                        "type": "number",
                        "description": "Minimum discount percentage to filter by (e.g., 10 for 10% off)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flash_deals",
            "description": "Get currently active flash deals and limited-time promotions. "
                           "Returns deals with title, discount, original price, deal price, "
                           "time remaining, and product details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of deals to return (default: 5, max: 20)",
                    },
                },
                "required": [],
            },
        },
    },
]

# ── System prompt ────────────────────────────────────────────────────────────

MARKETING_SYSTEM_PROMPT = """You are a marketing and promotions specialist for SnapTrip, a travel e-commerce platform.

Your job is to help users find the best deals, coupons, and promotions available.

Guidelines:
1. Use 'get_coupons' to find available discount codes. Filter by category if the user
   has a specific interest (hotels, flights, tours, packages).
2. Use 'get_flash_deals' to show limited-time promotional deals.
3. Present deals and coupons in a clear, exciting way. Highlight the savings percentage
   and any urgency (e.g., "ends in 2 hours").
4. If there are no matching coupons, suggest checking flash deals or broader categories.
5. Never make up deals — only report what the tools return.
6. NEVER call a tool that you don't have defined.

Respond in the user's language. Be enthusiastic but honest.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


async def marketing_engine_node(state: PlanState) -> dict:
    """Handle coupon/promotion queries. Calls get_coupons, get_flash_deals tools.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    from agent.graph import _runtime

    adapter = _runtime.llm_adapter if _runtime else None
    if not adapter:
        logger.error("marketing_engine: LLM adapter unavailable")
        return {"phase": "error", "status": "llm_unavailable"}

    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)

    if retry_count > 3:
        logger.warning("marketing_engine: max retries exceeded, forcing synthesize")
        return {"phase": "marketing_handling", "status": "max_retries"}

    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": MARKETING_SYSTEM_PROMPT},
    ]
    for msg in messages:
        if hasattr(msg, "type"):
            role = msg.type
            content = msg.content or ""
            role_map = {"human": "user", "ai": "assistant", "tool": "tool"}
            api_role = role_map.get(role, role)
            entry: dict[str, Any] = {"role": api_role, "content": content}
            if role == "ai":
                tcs = getattr(msg, "tool_calls", None) or []
                if tcs:
                    from agent.utils import normalize_tool_calls_for_api
                    entry["tool_calls"] = normalize_tool_calls_for_api(tcs)
            if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            llm_messages.append(entry)
        elif isinstance(msg, dict):
            llm_messages.append(msg)

    try:
        response = await adapter.chat(
            messages=llm_messages,
            tools=MARKETING_TOOLS,
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("marketing_engine: LLM call failed")
        return {"phase": "error", "status": "llm_error"}

    return {
        "messages": [response],
        "phase": "marketing_handling",
        "current_agent": "marketing_engine",
        "retry_count": retry_count + 1,
    }
