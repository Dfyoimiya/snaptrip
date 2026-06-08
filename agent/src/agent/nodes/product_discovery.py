"""Product Discovery — ReAct agent for product search and recommendations.

Calls search_products and get_product_detail tools.
Supports multi-turn: LLM -> tools -> LLM -> final answer.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions (OpenAI function-calling format) ────────────────────────

PRODUCT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the product catalog for travel products matching user criteria. "
                           "Uses semantic search across hotels, flights, tours, and packages. "
                           "Returns ranked list of matching products with prices and descriptions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query describing what the user wants",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["hotel", "flight", "tour", "package", "all"],
                        "description": "Product category filter. Default is 'all'.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5, max: 20)",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["relevance", "price_asc", "price_desc", "rating"],
                        "description": "Sort order for results (default: 'relevance')",
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
                           "Returns full description, pricing, availability, reviews, and images.",
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
]

# ── System prompt ────────────────────────────────────────────────────────────

PRODUCT_SYSTEM_PROMPT = """You are a travel product specialist for SnapTrip, a travel e-commerce platform.

Your job is to help users find the best travel products (hotels, flights, tours, packages).

Guidelines:
1. Use 'search_products' to find products matching the user's search criteria.
2. Use 'get_product_detail' to get full details on specific products the user is interested in.
3. Be conversational and helpful. Summarize results clearly with key details like
   name, price, rating, and highlights.
4. If the user provides specific filters (budget, dates, destination), pass them
   in the search query.
5. If no results are found, suggest broadening the search criteria.
6. Present up to 3-5 best matches, not an exhaustive list.
7. NEVER call a tool that you don't have defined.

Respond in the user's language. Be concise but informative.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


async def product_discovery_node(state: PlanState) -> dict:
    """Search products based on user intent. Calls search_products/get_product_detail tools.

    On first turn: sends user query + system prompt to LLM with tool definitions.
    On subsequent turns (after tool results): LLM processes tool output and either
    calls more tools or returns a final answer.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    from agent.graph import _runtime

    adapter = _runtime.llm_adapter if _runtime else None
    if not adapter:
        logger.error("product_discovery: LLM adapter unavailable")
        return {"phase": "error", "status": "llm_unavailable"}

    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)

    if retry_count > 3:
        logger.warning("product_discovery: max retries exceeded, forcing synthesize")
        return {"phase": "product_searching", "status": "max_retries"}

    # Build messages: system prompt + accumulated conversation
    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": PRODUCT_SYSTEM_PROMPT},
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
            tools=PRODUCT_TOOLS,
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("product_discovery: LLM call failed")
        return {"phase": "error", "status": "llm_error"}

    return {
        "messages": [response],
        "phase": "product_searching",
        "current_agent": "product_discovery",
        "retry_count": retry_count + 1,
    }
