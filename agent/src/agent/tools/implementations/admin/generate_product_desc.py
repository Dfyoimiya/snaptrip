"""Generate product description tool — LLM-only, no HTTP calls.

Uses hardcoded templates to produce SEO-friendly product descriptions,
suggestions, and keywords based on the product name, category, and features.
"""

from __future__ import annotations

import random
from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

# ── Description templates per style ──────────────────────────────────────────

_PROFESSIONAL_TEMPLATES = [
    "Introducing the {name} — a premium {category} solution designed for modern travelers. "
    "Featuring {features}, this product delivers exceptional quality and reliability. "
    "Backed by our satisfaction guarantee.",
    "The {name} redefines {category} excellence. With {features}, it stands out as "
    "a top-tier choice for discerning customers seeking the best in travel gear. "
    "Engineered for performance and built to last.",
    "Discover the {name}, the ultimate {category} for your next adventure. "
    "Key highlights include {features}, making it an indispensable companion. "
    "Order today and experience the difference.",
]

_CASUAL_TEMPLATES = [
    "Meet the {name} — your new favorite {category}! Packed with {features}, "
    "it's the perfect sidekick for your travels. Grab yours while supplies last!",
    "Looking for an awesome {category}? The {name} is exactly what you need. "
    "Features {features} — yep, it's that good. Get it now!",
    "Say hello to the {name}! This {category} is loaded with {features} and "
    "ready for any adventure. Don't miss out — shop the collection today!",
]

_MARKETING_TEMPLATES = [
    "BEST DEAL {name} – Exclusive Limited-Time Offer! "
    "This premium {category} comes with {features} — unbeatable value for savvy travelers. "
    "Sale ends soon. Click to claim your discount!",
    "FLASH SALE The {name} is flying off the shelves! "
    "As a top-rated {category} featuring {features}, this deal won't last. "
    "Limited stock — secure yours now at the lowest price!",
    "SPECIAL PROMOTION Upgrade your travel gear with the {name}. "
    "This {category} includes {features} and is available at a members-only price. "
    "Join thousands of happy customers today!",
]

# ── Keyword sets per category ────────────────────────────────────────────────

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "hotel": ["hotel booking", "luxury stay", "room reservation", "best hotel deal", "accommodation"],
    "flight": ["flight ticket", "airfare deal", "cheap flights", "airline booking", "travel airfare"],
    "tour": ["guided tour", "sightseeing", "travel package", "local experience", "day trip"],
    "package": ["travel package", "all-inclusive", "vacation deal", "holiday package", "bundle deal"],
    "ticket": ["attraction ticket", "entry pass", "skip the line", "admission", "entry ticket"],
    "gear": ["travel gear", "luggage", "backpack", "travel accessories", "essentials"],
}


def _pick_keywords(category: str) -> list[str]:
    """Pick default keywords based on category."""
    cat_lower = category.lower()
    for key, kwds in _CATEGORY_KEYWORDS.items():
        if key in cat_lower:
            return kwds[:5]
    return ["travel product", "best deal", "online shop", "quality", "fast delivery"]


def _pick_templates(style: str) -> list[str]:
    style_lower = style.lower()
    if style_lower == "casual":
        return _CASUAL_TEMPLATES
    if style_lower == "marketing":
        return _MARKETING_TEMPLATES
    return _PROFESSIONAL_TEMPLATES


class GenerateProductDescArgs(BaseModel):
    product_name: str = Field(..., description="Product name")
    category: str = Field("", description="Product category")
    features: str = Field("", description="Key features, comma-separated")
    style: str = Field("professional", description="Style: professional, casual, marketing")


class GenerateProductDescTool(SmartDayBaseTool):
    name: str = "generate_product_desc"
    description: str = (
        "Generate SEO-friendly product descriptions using templates. "
        "Produces 3 description suggestions and keyword list. "
        "No external API calls — runs entirely client-side."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GenerateProductDescArgs
    tool_timeout: float = 2.0

    async def _arun(self, **kwargs: Any) -> dict:
        product_name = kwargs.get("product_name", "")
        category = kwargs.get("category", "") or "travel product"
        features = kwargs.get("features", "") or "premium quality, reliable performance"
        style = kwargs.get("style", "professional")

        # Normalize feature list: split by comma and join with commas
        feature_items = [f.strip() for f in features.split(",") if f.strip()]
        if not feature_items:
            feature_items = ["premium quality", "reliable performance"]
        feature_text = ", ".join(feature_items)

        templates = _pick_templates(style)

        suggestions: list[str] = []
        for tpl in templates:
            desc = tpl.format(name=product_name, category=category, features=feature_text)
            suggestions.append(desc)

        keywords = _pick_keywords(category)
        # Add product-name-derived keywords
        name_parts = [p.strip().lower() for p in product_name.split() if len(p.strip()) > 2]
        keywords = name_parts + keywords

        return {
            "product_name": product_name,
            "category": category,
            "style": style,
            "suggestions": suggestions,
            "keywords": keywords,
        }

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
