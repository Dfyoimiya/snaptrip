"""Customer Service — after-sales support, complaints, order inquiries, return/refund guidance.

A ReAct specialist that handles the full spectrum of C2B customer service:
  - Order status & logistics tracking
  - Return/refund eligibility & process guidance
  - Complaint intake & escalation
  - Product inquiries in a service context
  - Coupon/compensation lookup
  - Policy & FAQ lookup

Reuses existing tools: query_order, cancel_order, search_knowledge, search_products,
get_product_detail, get_coupons.

Phase 2 will add CS-specific tools: submit_return_request, create_support_ticket, etc.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from agent.nodes.base import BaseSpecialist
from agent.nodes.emotion import detect_emotion, detect_emotion_trajectory, emotion_to_tone_hint
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions ─────────────────────────────────────────────────────────

CS_TOOLS: list[dict[str, Any]] = [
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
            "DO NOT use if the order is already shipped — guide user to return/refund process instead.",
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
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the knowledge base for FAQs, return/refund policies, "
            "shipping policies, warranty information, payment methods, account management, "
            "and other customer service topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query for the knowledge base",
                    },
                    "topic": {
                        "type": "string",
                        "enum": [
                            "payment",
                            "account",
                            "cancellation",
                            "refund",
                            "return",
                            "shipping",
                            "warranty",
                            "complaint",
                            "general",
                            "all",
                        ],
                        "description": "Topic filter to narrow results (default: 'all')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 3, max: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the product catalog. In customer service context, use this "
            "to look up products the user is asking about, or to suggest alternatives "
            "when a return/exchange is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query describing what the user wants",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_detail",
            "description": "Get detailed information about a specific product by its ID. "
            "Useful for verifying product specifications, warranty terms, or pricing "
            "when handling customer inquiries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Unique product identifier",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_coupons",
            "description": "Get available coupons and discount codes. In customer service context, "
            "use this to find compensation coupons or check what coupons a user already has.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["available", "mine"],
                        "description": "'available' for all coupons, 'mine' for user's claimed coupons (default: 'mine')",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_return_eligibility",
            "description": "Check if an order is eligible for return/refund. "
            "Returns eligibility status, order status, days since delivery, and policy limits. "
            "ALWAYS call this BEFORE submit_return_request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to check return eligibility for",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_return_request",
            "description": "Submit a return/refund request for an order. "
            "ONLY use after confirming eligibility via check_return_eligibility. "
            "Creates a return application that will be reviewed by admin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to submit return for",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for return (required)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Additional description of the issue",
                    },
                    "product_count": {
                        "type": "integer",
                        "description": "Number of items to return (default: 1)",
                    },
                },
                "required": ["order_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_refund_status",
            "description": "Query the refund/return status for an order. "
            "Returns whether a return was requested, current status, refund amount, and timeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to query refund status for",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_logistics",
            "description": "Query shipping and delivery information for an order. "
            "Returns order status, tracking number if available, and delivery info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to check logistics for",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_order_complaint",
            "description": "Validate whether a customer complaint about an order is justified. "
            "Checks order existence, user ownership, order status, and previous complaint history. "
            "Use this FIRST when a user makes a complaint.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to validate complaint for",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Create a support ticket to escalate an issue to human customer service. "
            "Use ONLY when the AI cannot resolve the problem: complex disputes, legal threats, "
            "severe complaints, or situations requiring manual intervention. "
            "Always explain to the user that you are escalating before calling this.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Ticket title summarizing the issue",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the problem",
                    },
                    "order_id": {
                        "type": "string",
                        "description": "Related order ID if applicable",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["complaint", "refund", "inquiry", "other"],
                        "description": "Ticket type (default: 'inquiry')",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["normal", "urgent", "critical"],
                        "description": "Priority level (default: 'normal')",
                    },
                },
                "required": ["title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_compensation_coupon",
            "description": "Issue a compensation coupon to a customer as service recovery. "
            "Use SPARINGLY — only when the company is clearly at fault "
            "(shipping delays, damaged items, wrong items sent, service failures). "
            "Requires order_id, amount in CNY, reason, and member_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID the compensation is related to",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Coupon amount in CNY (e.g., 10.00)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for compensation",
                    },
                    "member_id": {
                        "type": "string",
                        "description": "Member ID to issue coupon to",
                    },
                },
                "required": ["order_id", "amount", "reason", "member_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_session_summary",
            "description": "Save a compressed summary of the current customer service conversation "
            "for long-term memory. Call this at the END of every CS session. "
            "The summary should include: what the issue was, what was done, "
            "the resolution status, and key entities (order IDs, product IDs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID to save summary for",
                    },
                    "intent": {
                        "type": "string",
                        "description": "CS intent of the session: cs_after_sales/cs_complaint/cs_inquiry",
                    },
                    "summary_text": {
                        "type": "string",
                        "description": "LLM-compressed summary of the conversation (3-5 sentences)",
                    },
                    "resolution_status": {
                        "type": "string",
                        "enum": ["resolved", "escalated", "abandoned", "unknown"],
                        "description": "Resolution status (default: 'unknown')",
                    },
                    "satisfaction_score": {
                        "type": "integer",
                        "description": "CSAT score 1-5 if collected",
                    },
                    "ticket_id": {
                        "type": "string",
                        "description": "Support ticket ID if escalated",
                    },
                    "order_id": {
                        "type": "string",
                        "description": "Related order ID",
                    },
                    "conversation_turns": {
                        "type": "integer",
                        "description": "Number of conversation turns",
                    },
                    "tools_called": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tool names called during the session",
                    },
                    "emotion_trajectory": {
                        "type": "string",
                        "description": "How user emotion changed: e.g., 'angry→calm', 'neutral→satisfied'",
                    },
                },
                "required": ["session_id", "summary_text"],
            },
        },
    },
]

# ── System prompt ────────────────────────────────────────────────────────────

CS_SYSTEM_PROMPT = """You are a professional and empathetic customer service agent for SnapTrip, an e-commerce platform.

Your job is to help customers with after-sales support, order issues, complaints, and general inquiries.

## Emotion Awareness:
At the start of each conversation, you will receive an "Emotion Context" hint about the user's
current emotional state (e.g., "The user is ANGRY."). Adjust your tone accordingly:
- ANGRY → Extra empathy, sincere apology, focus on concrete solutions, never defensive
- FRUSTRATED → Acknowledge patience, clear timeline, show urgency
- ANXIOUS → Reassurance, clear next steps, offer follow-up
- SATISFIED → Wrap up efficiently, ask if they need anything else
- NEUTRAL → Professional and helpful

## Core Capabilities:
1. **Order Lookup** — Use 'query_order' to check order status, shipping progress, and details.
   If the user doesn't provide an order ID, ask politely or use 'latest' for the most recent order.
2. **Order Cancellation** — Use 'cancel_order' for orders not yet shipped. If already shipped,
   explain the return/refund process instead.
3. **Return/Refund** — Use 'check_return_eligibility' FIRST to verify the order qualifies.
   Then use 'submit_return_request' to create the application. Use 'query_refund_status' to
   check refund progress. NEVER submit a return without checking eligibility first.
4. **Complaint Handling** — Use 'validate_order_complaint' FIRST to verify the complaint is
   valid (order exists, belongs to user, status allows). Then decide: return/refund or escalate.
5. **Logistics** — Use 'check_logistics' for shipping/delivery status queries.
6. **Policy Lookup** — Use 'search_knowledge' for FAQs, return/refund policies, shipping info,
   warranty terms, payment methods, and account-related questions. ALWAYS search before answering
   policy questions — never guess.
7. **Product Info** — Use 'search_products' and 'get_product_detail' to look up products the user
   asks about, or to suggest alternatives during return/exchange discussions.
8. **Coupons/Compensation** — Use 'get_coupons' to check available coupons. Use
   'issue_compensation_coupon' SPARINGLY — only when the company is clearly at fault.
9. **Escalation** — Use 'create_support_ticket' when the situation exceeds AI capabilities:
   legal threats, complex disputes, severe complaints, or explicit requests for human support.
10. **Session Memory** — At the END of every CS conversation, call 'save_session_summary' to
   persist a compressed summary. Include: what the issue was, what was done, resolution status,
   key entities (order IDs, product IDs), tools called, and emotional trajectory.

## Service Guidelines:
1. **Empathy first**: Acknowledge the customer's feelings before diving into solutions.
   Order problems and complaints can be frustrating.
2. **Be specific**: Quote exact order status, policy terms, timelines, and amounts from tool results.
   Never fabricate information.
3. **Set expectations**: Clearly state next steps, timelines, and what the customer needs to do.
4. **Escalation awareness**: If a situation cannot be resolved with available tools (severe complaints,
   complex disputes, legal threats), use 'create_support_ticket' to escalate to human support.
   Always explain to the user what's happening before escalating.
5. **No false promises**: Never promise refund amounts, compensation, or timelines that are not
   confirmed by tool results or policy.
6. **Privacy conscious**: Do not ask for or expose sensitive personal data (full card numbers,
   passwords, ID numbers). Order IDs and registered email/phone are acceptable.
7. **De-escalation**: For angry customers, stay calm, apologize sincerely, and focus on solutions.

## After-Sales Scenarios:
- **Return/Refund inquiry**: check_return_eligibility → if eligible → submit_return_request.
  If not eligible → explain why + suggest alternatives.
- **Shipping delay**: check_logistics → explain current status → check shipping policy for
  delay compensation terms → consider issue_compensation_coupon if company is at fault.
- **Wrong/damaged item**: validate_order_complaint → search_knowledge for policy →
  check_return_eligibility → submit_return_request or create_support_ticket.
- **Complaint**: validate_order_complaint FIRST → if valid, offer return/refund or compensation.
  If invalid, explain why politely. If severe, create_support_ticket.

## Response Format:
When providing a final answer (without tool calls), structure as JSON:
{"answer": "Your customer service response here", "highlights": ["Key point 1", "Next step"]}

Always respond in the user's language. Be warm but professional.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


class CustomerServiceNode(BaseSpecialist):
    node_name = "customer_service"
    system_prompt = CS_SYSTEM_PROMPT
    tools = CS_TOOLS
    phase_name = "customer_service"
    temperature = 0.3

    def _build_messages(self, state: PlanState) -> list[dict[str, Any]]:
        """Inject emotion context into system prompt before LLM call."""
        messages = state.get("messages", [])
        # Detect emotion from recent user messages
        user_text = ""
        for msg in reversed(messages):
            role = getattr(msg, "type", None)
            if role == "human":
                user_text = str(getattr(msg, "content", "") or "")
                break

        emotion, _ = detect_emotion(user_text)
        tone_hint = emotion_to_tone_hint(emotion)

        # Detect emotion trajectory for multi-turn conversations
        trajectory = detect_emotion_trajectory(messages)

        # Build system prompt with emotion context
        enhanced_prompt = self.system_prompt
        if tone_hint:
            enhanced_prompt = (
                f"## Emotion Context:\n{tone_hint}\n\n{self.system_prompt}"
            )

        llm_messages: list[dict[str, Any]] = [
            {"role": "system", "content": enhanced_prompt},
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

        # Store detected emotion in working_memory for session summary
        wm = dict(state.get("working_memory", {}))
        wm["emotion"] = emotion
        if trajectory:
            wm["emotion_trajectory"] = trajectory

        return llm_messages


_instance = CustomerServiceNode()


async def customer_service_node(state: PlanState) -> dict:
    """Handle customer service queries: orders, after-sales, complaints, policies.

    Injects emotion detection into the system prompt for tone adjustment.
    Uses 14 tools including return processing, ticket creation, and session memory.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    return cast(dict, await _instance.execute(state))
