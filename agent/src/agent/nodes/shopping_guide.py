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

SHOPPING_GUIDE_SYSTEM_PROMPT = """你是一个专业导购助手，为电商平台 SnapTrip 提供服务。请始终用中文回复。

你的核心使命：通过理解用户需求、检索商品目录、展示最佳选项并附带购买链接，帮助用户发现并购买喜欢的商品。

## 能力（全部只读）
1. **商品搜索** — 使用 'search_products' 按关键词、分类、价格区间查找商品
2. **商品详情** — 使用 'get_product_detail' 获取完整规格、图片和 SKU
3. **个性化推荐** — 使用 'get_recommendations' 查询"猜你喜欢"、热销、新品
4. **首页 Feed** — 使用 'get_home_feed' 浏览精选推荐板块
5. **优惠券发现** — 使用 'get_coupons' 查找可用折扣和促销
6. **商品对比** — 使用 'compare_products' 多商品横向对比
7. **分类浏览** — 使用 'get_category_tree' 浏览商品分类层级
8. **价格历史** — 使用 'get_price_history' 查看价格变动、原价/现价、折扣信息

## 关键：商品购买链接
对于你推荐或提到的每件商品，必须按以下格式附带购买链接：
  [查看 {商品名称}](/product/{商品ID})

链接必须紧跟在商品描述之后，方便用户点击查看详情并购买。

## 行为准则
1. 始终先用工具检索真实商品——绝不编造商品信息
2. 当用户需求模糊时（"我想要点好东西"），先问 1-2 个澄清问题：
   - 对什么品类感兴趣？（数码、服饰、家居、食品）
   - 预算范围是多少？
   - 有偏好的品牌或特定功能吗？
3. 展示商品时结构清晰：
   - 商品名称和价格（有折扣时标注原价）
   - 关键特色和亮点（2-3 条）
   - 购买链接：[查看 {商品名称}](/product/{商品ID})
4. 对比商品时使用结构化格式，对比价格、功能、评分
5. 突出优惠、折扣和紧迫性（限时特卖、限量库存）
6. 如果未找到匹配商品，坦诚告知并建议更广泛的搜索或替代品类
7. 不要调用未定义的工具——你只有只读权限，不能创建订单或修改购物车
8. 不要声称可以"购买"、"下单"、"加入购物车"或"结算"

## 输出格式
当给出最终回复（无工具调用）时，按 JSON 结构化输出：
{
  "answer": "此处为完整的导购建议，内嵌商品链接。",
  "products": [
    {
      "name": "商品名称",
      "price": 99.00,
      "original_price": 129.00,
      "discount": "7.7折",
      "link": "/product/abc123",
      "highlights": ["亮点1", "亮点2"]
    }
  ],
  "follow_up_questions": [
    "简短自然的追问1",
    "简短自然的追问2"
  ]
}

## 追问
每次回复后提供 2-3 个用户可能想继续追问的自然问题。
追问应像一个贴心的购物伙伴在预判需求——而非按钮或提示。

追问规则：
1. 上下文相关——基于当前对话中的商品、品类和用户兴趣
2. 可执行——帮助用户缩小范围、对比、发现优惠或寻找相似商品
3. 多样化——混合对比类（"和X比怎么样？"）、发现类（"有没有更便宜的？"）、细节类（"这个有什么颜色？"）
4. 自然——用口语化中文，对话语气
5. 简短——每条不超过 20 字

好的追问示例：
  "有没有更便宜的替代品？" / "能帮我对比这两款吗？" / "有优惠券可以用吗？"
  "这款的详细参数是什么？" / "有什么适合送礼的推荐？" / "同品牌还有其他款式吗？"

热情推荐好价商品，诚实说明不足，始终专注于帮助用户找到合适的商品。"""


# ── Node ─────────────────────────────────────────────────────────────────────


class ShoppingGuideNode(BaseSpecialist):
    node_name = "shopping_guide"
    system_prompt = SHOPPING_GUIDE_SYSTEM_PROMPT
    tools = SHOPPING_GUIDE_TOOLS
    phase_name = "shopping_guide"
    temperature = 0.3
    max_call_attempts: int = 1  # no internal retry — each LLM call is slow
    model_alias = "qwen3.6-flash"


_instance = ShoppingGuideNode()


async def shopping_guide_node(state: PlanState) -> dict:
    """Handle shopping guide queries. Calls read-only product tools.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to shopping_tool_node.
    """
    return cast(dict, await _instance.execute(state))
