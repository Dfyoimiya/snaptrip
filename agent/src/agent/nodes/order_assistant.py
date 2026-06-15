"""Order Assistant — query order status, cancel orders, request refunds."""

from __future__ import annotations

import logging
from typing import Any, cast

from agent.nodes.base import BaseSpecialist
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

When providing a final answer (without tool calls), structure your response as JSON:
{"answer": "Your order status/cancellation summary here", "highlights": ["Order status", "Next steps"]}

Respond in the user's language.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


class OrderAssistantNode(BaseSpecialist):
    node_name = "order_assistant"
    system_prompt = ORDER_SYSTEM_PROMPT
    tools = ORDER_TOOLS
    phase_name = "order_handling"
    temperature = 0.3


_instance = OrderAssistantNode()


async def order_assistant_node(state: PlanState) -> dict:
    """Handle order-related queries. Calls query_order, cancel_order tools.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    return cast(dict, await _instance.execute(state))
