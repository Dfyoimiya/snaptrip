"""Supervisor — intent classification and conditional routing.

Classifies user input into intents:
  - product_search    -> product_discovery
  - order_status      -> order_assistant
  - cs_after_sales    -> customer_service   (return/refund/exchange)
  - cs_complaint      -> customer_service   (complaints, disputes)
  - cs_inquiry        -> customer_service   (shipping, account, policy)
  - coupon_inquiry    -> marketing_engine
  - admin_analytics   -> admin_analyst
  - general           -> knowledge_qa

Uses keyword-based fallback when LLM is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Keyword-based intent classification (fallback) ───────────────────────────

INTENT_KEYWORDS: dict[str, list[str]] = {
    "product_search": [
        "search",
        "find",
        "product",
        "recommend",
        "recommendation",
        "buy",
        "purchase",
        "shop",
        "item",
        "price",
        "catalog",
        "looking for",
        "show me",
        "what do you have",
        "available",
        "deal price",
        "cheapest",
        "best",
        "hotel",
        "flight",
        "ticket",
        "trip",
        "travel",
        "vacation",
        "tour",
        "package",
    ],
    "cs_after_sales": [
        "refund",
        "return",
        "exchange",
        "退货",
        "退款",
        "换货",
        "退换",
        "money back",
        "get my money",
        "send back",
        "return policy",
        "refund policy",
        "refund status",
        "refund progress",
        "退钱",
        "退单",
        "退换货",
        "退货流程",
        "退款进度",
    ],
    "cs_complaint": [
        "complaint",
        "complain",
        "投诉",
        "damaged",
        "broken",
        "defective",
        "not working",
        "wrong item",
        "不满意",
        "差评",
        "质量",
        "有问题",
        "坏的",
        "破损",
        "损坏",
        "fake",
        "假货",
        "过期",
        "expired",
        "missing",
        "缺少",
        "漏发",
        "never arrived",
        "没收到",
    ],
    "cs_inquiry": [
        "shipping",
        "delivery",
        "物流",
        "快递",
        "发货",
        "delivered",
        "shipment",
        "tracking",
        "where is my",
        "when will",
        "多久到",
        "什么时候到",
        "还没到",
        "modify address",
        "change address",
        "修改地址",
        "修改订单",
        "payment method",
        "付款方式",
        "支付方式",
        "how to pay",
        "account",
        "register",
        "sign up",
        "login",
        "password",
        "重置密码",
        "forgot password",
        "忘记密码",
    ],
    "order_status": [
        "order",
        "status",
        "cancel",
        "my order",
        "order number",
        "modify order",
        "change order",
        "update order",
        "取消订单",
        "订单状态",
        "订单号",
        "我的订单",
    ],
    "coupon_inquiry": [
        "coupon",
        "discount",
        "promo",
        "promotion",
        "deal",
        "flash",
        "sale",
        "offer",
        "voucher",
        "code",
        "off",
        "save money",
        "cheaper",
        "discount code",
        "special offer",
        "limited time",
    ],
    "general": [
        "faq",
        "help",
        "how to",
        "policy",
        "contact",
        "support",
        "information",
        "about",
        "hours",
        "location",
        "store",
        "gift card",
    ],
    "admin_analytics": [
        "sales",
        "revenue",
        "report",
        "dashboard",
        "analytics",
        "stock",
        "inventory",
        "low stock",
        "trend",
        "statistics",
        "member",
        "insight",
        "description",
        "seo",
        "generate",
        "coupon analysis",
        "effect",
        "performance",
        "增长",
        "数据",
        "有多少",
        "多少会员",
        "新增",
        "增长情况",
        "会员增长",
        "会员数据",
        "会员统计",
        "商品描述",
        "商品详情",
        "描述生成",
    ],
}


def _classify_intent_keywords(text: str) -> tuple[str, float]:
    """Keyword-based fallback classification. Returns (intent, confidence)."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        scores[intent] = sum(1 for kw in keywords if kw.lower() in text_lower)
    if not scores or max(scores.values()) == 0:
        return ("general", 0.3)
    best_intent = max(scores, key=lambda k: scores[k])
    # Confidence: score / total keyword hits across all intents
    total_hits = sum(scores.values())
    confidence = scores[best_intent] / total_hits if total_hits > 0 else 0.3
    return (best_intent, round(confidence, 2))


# ── LLM-based classification prompt ──────────────────────────────────────────

SUPERVISOR_SYSTEM_PROMPT = """You are an intent classifier for SnapTrip, an e-commerce platform.

Classify the user's message into exactly ONE of these intents:

1. product_search   — User wants to search, browse, or discover products
2. order_status     — User wants to check order status or cancel an order.
                       Simple order lookups and cancellations only.
3. cs_after_sales   — User wants to RETURN, REFUND, or EXCHANGE a product.
                       KEY SIGNALS: refund request, return process, money back,
                       exchange for different size/color, return eligibility.
                       This is DIFFERENT from order_status — it's about AFTER-SALES
                       service, not just checking what happened to an order.
4. cs_complaint     — User is COMPLAINING or expressing dissatisfaction.
                       KEY SIGNALS: damaged item, broken product, wrong item received,
                       quality issues, expired goods, missing items, never arrived,
                       angry or frustrated tone about a purchase.
5. cs_inquiry       — User has a general customer service question:
                       shipping/delivery timelines, payment methods, account issues
                       (login, password reset, registration), how to order,
                       address changes, store locations.
6. coupon_inquiry   — User wants coupons, discounts, promo codes, flash deals,
                       or special offers.
7. admin_analytics  — User wants DATA or ANALYTICS: sales reports, inventory alerts,
                       order trends, member growth/statistics/insights, product
                       description generation, or coupon effect analysis.
8. general          — User has a general question that doesn't fit the above:
                       FAQ about the platform, company info, gift cards, etc.

CRITICAL DISTINCTIONS:
- "I want a refund" → cs_after_sales (NOT order_status)
- "My product is broken" → cs_complaint (NOT general)
- "When will my order arrive" → cs_inquiry (NOT order_status)
- "Where is my order" → order_status (simple tracking)

Reply with ONLY a JSON object: {"intent": "<intent_name>", "confidence": <0.0-1.0>}
"""


async def _classify_intent_llm(text: str) -> tuple[str, float]:
    """Use LLM to classify user intent. Returns (intent, confidence)."""
    from agent.graph import _runtime

    adapter = _runtime.llm_adapter if _runtime else None
    if not adapter:
        return _classify_intent_keywords(text)

    try:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        response = await adapter.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=128,
            stream=False,
        )
        content = response.content if hasattr(response, "content") else str(response)
        import json

        result = json.loads(content if isinstance(content, str) else str(content))
        intent = result.get("intent", "general")
        confidence = float(result.get("confidence", 0.5))
        valid_intents = {
            "product_search",
            "order_status",
            "cs_after_sales",
            "cs_complaint",
            "cs_inquiry",
            "coupon_inquiry",
            "admin_analytics",
            "general",
        }
        if intent not in valid_intents:
            intent = "general"
            confidence = 0.3
        return (intent, round(confidence, 2))
    except Exception:
        logger.warning(
            "supervisor: LLM classification failed, falling back to keywords",
            exc_info=True,
        )
        return _classify_intent_keywords(text)


# ── Node ─────────────────────────────────────────────────────────────────────


async def supervisor_node(state: PlanState) -> dict:
    """Classify intent and route to specialist agent.

    Extracts the last user message, classifies intent (LLM or keyword fallback),
    and sets the routing fields in state.

    Returns:
        dict with intent, intent_confidence, current_agent, retry_count
    """
    messages = state.get("messages", [])
    user_text = ""
    for msg in reversed(messages):
        role = getattr(msg, "type", None)
        if role == "human":
            user_text = getattr(msg, "content", "") or ""
            break
    if not user_text:
        # Try dict format
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("type") == "human":
                user_text = str(msg.get("content", ""))
                break

    intent, confidence = await _classify_intent_llm(user_text)

    logger.info(
        "supervisor: intent=%s confidence=%s text=%s",
        intent,
        confidence,
        user_text[:100],
    )

    return {
        "intent": intent,
        "intent_confidence": confidence,
        "current_agent": intent,
        "retry_count": 0,
        "sub_results": {},
        "product_results": [],
        "order_detail": None,
    }


# ── Routing function (used in graph conditional edges) ───────────────────────


def route_by_intent(state: PlanState) -> str:
    """Conditional routing function for graph edges.

    Maps the classified intent to the corresponding specialist node name.
    CS intents (cs_after_sales, cs_complaint, cs_inquiry) all route to customer_service.
    """
    intent = state.get("intent", "general")
    routes: dict[str, str] = {
        "product_search": "product_discovery",
        "order_status": "order_assistant",
        "cs_after_sales": "customer_service",
        "cs_complaint": "customer_service",
        "cs_inquiry": "customer_service",
        "coupon_inquiry": "marketing_engine",
        "admin_analytics": "admin_analyst",
        "general": "knowledge_qa",
    }
    return routes.get(intent, "knowledge_qa")
