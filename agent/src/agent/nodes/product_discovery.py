"""Product Discovery — ReAct agent for product search and recommendations.

Calls search_products and get_product_detail tools.
Supports multi-turn: LLM -> tools -> LLM -> final answer.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from agent.nodes.base import BaseSpecialist
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions (OpenAI function-calling format) ────────────────────────

PRODUCT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the product catalog for products matching user criteria. "
            "Supports keyword search across all product categories. "
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
                        "enum": ["electronics", "clothing", "home", "sports", "beauty", "food", "all"],
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

PRODUCT_SYSTEM_PROMPT = """You are a product specialist for SnapTrip, an e-commerce platform.

Your job is to help users find products across all categories.

Guidelines:
1. Use 'search_products' to find products matching the user's search criteria.
2. Use 'get_product_detail' to get full details on specific products the user is interested in.
3. Be conversational and helpful. Summarize results clearly with key details like
   name, price, rating, and highlights.
4. If the user provides specific filters (budget, price range, brand), pass them
   in the search query.
5. If no results are found, suggest broadening the search criteria.
6. Present up to 3-5 best matches, not an exhaustive list.
7. NEVER call a tool that you don't have defined.

When providing a final answer (without tool calls), structure your response as JSON:
{"answer": "Your product recommendations here", "highlights": ["Product 1 - ¥price", "Product 2 - ¥price"]}

Respond in the user's language. Be concise but informative.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


class ProductDiscoveryNode(BaseSpecialist):
    node_name = "product_discovery"
    system_prompt = PRODUCT_SYSTEM_PROMPT
    tools = PRODUCT_TOOLS
    phase_name = "product_searching"
    temperature = 0.3


_instance = ProductDiscoveryNode()


async def product_discovery_node(state: PlanState) -> dict:
    """Search products based on user intent. Calls search_products/get_product_detail tools.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    return cast(dict, await _instance.execute(state))
