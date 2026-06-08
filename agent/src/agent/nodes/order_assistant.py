"""Order Assistant — query order status, cancel orders, request refunds."""

from __future__ import annotations

import logging
from typing import Any

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions ─────────────────────────────────────────────────────────

ORDER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "Query order status and details by order number or user identity. "
                           "Returns order ID, status, items, payment, shipping info, and timeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order number or ID. If unknown, pass 'latest' to get most recent order.",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an order that has not yet been shipped. "
                           "Returns confirmation or rejection with reason. "
                           "DO NOT use if the order is already shipped — direct user to support instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to cancel",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for cancellation (optional, helps improve service)",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
]

# ── System prompt ────────────────────────────────────────────────────────────

ORDER_SYSTEM_PROMPT = """You are an order assistant for SnapTrip, a travel e-commerce platform.

Your job is to help users with order-related tasks: checking status, tracking shipments,
cancelling orders, and explaining refund policies.

Guidelines:
1. Use 'query_order' to look up an order by ID. If the user does not provide an order ID,
   ask for it politely. You can use 'latest' to fetch their most recent order.
2. Use 'cancel_order' to cancel an order. ONLY cancel if the order status allows it.
   If the order is already shipped, explain that they need to request a return instead.
3. Be empathetic and professional. Order issues can be stressful for users.
4. Summarize order status clearly: what stage it's at, expected delivery, and next steps.
5. For cancellations, confirm the cancellation and explain refund timeline.
6. NEVER call a tool that you don't have defined.

Respond in the user's language.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


async def order_assistant_node(state: PlanState) -> dict:
    """Handle order-related queries. Calls query_order, cancel_order tools.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    from agent.graph import _runtime

    adapter = _runtime.llm_adapter if _runtime else None
    if not adapter:
        logger.error("order_assistant: LLM adapter unavailable")
        return {"phase": "error", "status": "llm_unavailable"}

    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)

    if retry_count > 3:
        logger.warning("order_assistant: max retries exceeded, forcing synthesize")
        return {"phase": "order_handling", "status": "max_retries"}

    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": ORDER_SYSTEM_PROMPT},
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
            tools=ORDER_TOOLS,
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("order_assistant: LLM call failed")
        return {"phase": "error", "status": "llm_error"}

    return {
        "messages": [response],
        "phase": "order_handling",
        "current_agent": "order_assistant",
        "retry_count": retry_count + 1,
    }
