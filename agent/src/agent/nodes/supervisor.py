"""Supervisor — intent classification and conditional routing.

Classifies user input into intents:
  - product_search  -> product_discovery
  - order_status    -> order_assistant
  - coupon_inquiry  -> marketing_engine
  - general         -> knowledge_qa

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
    "order_status": [
        "order",
        "status",
        "tracking",
        "where is my",
        "delivery",
        "shipping",
        "cancel",
        "refund",
        "return",
        "my order",
        "order number",
        "when will",
        "delivered",
        "shipment",
        "modify order",
        "change order",
        "update order",
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
        "payment method",
        "account",
        "register",
        "sign up",
        "login",
        "password",
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

SUPERVISOR_SYSTEM_PROMPT = """You are an intent classifier for SnapTrip, a travel e-commerce platform.

Classify the user's message into exactly ONE of these intents:

1. product_search   — User wants to search, browse, or discover travel products
                       (hotels, flights, packages, tours, tickets, etc.)
                       Also: "what products do I have", "show me products", "in-stock items"
2. order_status     — User wants to check order status, tracking, cancel,
                       refund, or return an order
3. coupon_inquiry   — User wants coupons, discounts, promo codes, flash deals,
                       or special offers
4. admin_analytics  — User wants DATA or ANALYTICS: sales reports, inventory alerts,
                       order trends, member growth/statistics/insights, product
                       description generation, or coupon effect analysis.
                       KEY SIGNAL: questions asking about numbers, growth, trends,
                       statistics, reports, or "how many" type analysis queries.
                       Also: requests to generate or improve product descriptions.
5. general          — User has a general question about policies, account,
                       payment methods, store info, or other FAQ topics.
                       NOTE: "member growth" is NOT general — it's admin_analytics.
                       NOTE: "what products are on sale" is product_search, NOT general.

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
    """
    intent = state.get("intent", "general")
    routes: dict[str, str] = {
        "product_search": "product_discovery",
        "order_status": "order_assistant",
        "coupon_inquiry": "marketing_engine",
        "admin_analytics": "admin_analyst",
        "general": "knowledge_qa",
    }
    return routes.get(intent, "knowledge_qa")
