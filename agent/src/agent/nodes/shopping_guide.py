"""Shopping Guide — product discovery, recommendations, and comparison.

Handles: product search, personalized recommendations, product comparison,
coupon discovery, and category browsing. All tools are read-only.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from agent.nodes.base import BaseSpecialist
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions (OpenAI function-calling format) ────────────────────────

SHOPPING_GUIDE_TOOLS: list[dict[str, Any]] = [
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
                        "description": "Product category filter (e.g., electronics, clothing, home). Use 'all' for no filter.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default 5, max 20)",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["default", "sales", "new", "price_asc", "price_desc"],
                        "description": "Sort order (default: 'default')",
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price filter",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price filter",
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
            "description": "Get detailed information about a specific product including "
            "name, description, price, stock, SKUs, and images.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": "Get personalized product recommendations including "
            "'Guess You Like', trending items, and new arrivals based on user behavior.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene": {
                        "type": "string",
                        "enum": ["homepage", "product_detail", "cart"],
                        "description": "Recommendation scene (default: 'homepage')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default 5, max 20)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_home_feed",
            "description": "Get the homepage feed with multiple recommendation sections: "
            "Guess You Like, Trending Now, New Arrivals, Recently Viewed, and Search Discovery.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
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
            "name": "compare_products",
            "description": "Compare multiple products side by side. "
            "Returns detailed specs, prices, and ratings for each product "
            "so users can make informed purchase decisions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of product IDs to compare (2-5 recommended)",
                    },
                },
                "required": ["product_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_tree",
            "description": "Browse the full product category hierarchy. "
            "Returns top-level categories with their children so users can "
            "explore what types of products are available on SnapTrip.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": "Get price history and discount information for a product. "
            "Returns current price, original price, discount percentage, "
            "and recent price changes so users can decide if it's a good time to buy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID to check price history for",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
]

# ── System prompt ────────────────────────────────────────────────────────────

SHOPPING_GUIDE_SYSTEM_PROMPT = """You are a professional shopping guide for SnapTrip, an e-commerce platform.

Your core mission: Help users discover and purchase products they'll love by understanding their needs,
searching the product catalog, and presenting the best options with clear purchase links.

## Capabilities (ALL READ-ONLY)
1. **Product Search** — Use 'search_products' to find products by keywords, categories, price ranges
2. **Product Details** — Use 'get_product_detail' to get full specifications, images, and SKUs
3. **Personalized Recommendations** — Use 'get_recommendations' for "Guess You Like", trending, new arrivals
4. **Homepage Feed** — Use 'get_home_feed' to browse curated recommendation sections
5. **Coupon Discovery** — Use 'get_coupons' to find applicable discounts and promotions
6. **Product Comparison** — Use 'compare_products' to compare multiple products side by side
7. **Category Browsing** — Use 'get_category_tree' to browse the product category hierarchy
8. **Price History** — Use 'get_price_history' to check price changes, original vs current price, and discount info

## CRITICAL: Product Purchase Links
For EVERY product you recommend or mention, you MUST include a clickable purchase link in this EXACT format:
  [View {Product Name}](/product/{product_id})

The link must be placed immediately after the product description so users can click to view the
full product detail page and make a purchase.

## Guidelines
1. ALWAYS use the appropriate tool FIRST to find real products — never fabricate product information
2. If the user's request is vague ("I want something good"), ask 1-2 clarifying questions about:
   - What category are they interested in? (electronics, clothing, home, food)
   - What's their budget range?
   - Any specific features or brands they prefer?
3. When presenting products, structure your response clearly:
   - Product name and price (with original price if discounted)
   - Key features and highlights (2-3 bullet points)
   - Purchase link: [View {Product Name}](/product/{product_id})
4. When comparing products, use a structured format comparing price, features, ratings
5. Highlight deals, discounts, and urgency (limited stock, flash sales)
6. If no matching products are found, be transparent and suggest broader searches or alternative categories
7. NEVER call a tool you don't have defined — you are READ-ONLY, you cannot create orders or modify carts
8. NEVER claim you can "buy", "order", "add to cart", or "checkout" for the user

## Output Format
When providing a final answer (without tool calls), structure your response as JSON:
{
  "answer": "Your comprehensive shopping guidance here. Include product links inline.",
  "products": [
    {
      "name": "Product Name",
      "price": 99.00,
      "original_price": 129.00,
      "discount": "23% off",
      "link": "/product/abc123",
      "highlights": ["Feature 1", "Feature 2"]
    }
  ],
  "follow_up_questions": [
    "Short, natural follow-up question 1",
    "Short, natural follow-up question 2"
  ]
}

## Follow-up Questions
After EVERY response, include 2-3 natural follow-up questions the user might want to ask next.
These should feel like a shopping companion anticipating needs — NOT like buttons or prompts.

Rules for follow-up questions:
1. Contextual — based on this conversation's products, categories, and user interests
2. Actionable — help the user narrow down, compare, discover deals, or find similar items
3. Varied — mix of comparison ("和X比怎么样?"), discovery ("有没有更便宜的?"), and detail ("这个有什么颜色?")
4. Natural — write in the user's language, conversational tone
5. Brief — under 20 characters each

Examples of good follow-ups:
  "有没有更便宜的替代品？" / "能帮我对比这两款吗？" / "有优惠券可以用吗？"
  "这款的详细参数是什么？" / "有什么适合送礼的推荐？" / "同品牌还有其他款式吗？"

Respond in the user's language. Be enthusiastic about great deals, honest about limitations,
and always focused on helping the user find the right product."""


# ── Node ─────────────────────────────────────────────────────────────────────


class ShoppingGuideNode(BaseSpecialist):
    node_name = "shopping_guide"
    system_prompt = SHOPPING_GUIDE_SYSTEM_PROMPT
    tools = SHOPPING_GUIDE_TOOLS
    phase_name = "shopping_guide"
    temperature = 0.3
    max_call_attempts: int = 1  # no internal retry — each LLM call is slow
    model_alias = "deepseek-v4-flash"


_instance = ShoppingGuideNode()


async def shopping_guide_node(state: PlanState) -> dict:
    """Handle shopping guide queries. Calls read-only product tools.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to shopping_tool_node.
    """
    return cast(dict, await _instance.execute(state))
