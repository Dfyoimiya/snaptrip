"""Generate product description tool — uses LLM to produce SEO-friendly copy.

Falls back to template-based generation when the LLM adapter is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

logger = logging.getLogger(__name__)

# ── Fallback templates (used when LLM is unavailable) ──────────────────────

_FALLBACK_TEMPLATES: dict[str, list[str]] = {
    "professional": [
        "Introducing the {name} — a premium {category} solution. Featuring {features}, "
        "this product delivers exceptional quality and reliability.",
        "The {name} redefines {category} excellence. With {features}, it stands out "
        "as a top-tier choice for discerning customers.",
        "Discover the {name}, the ultimate {category} for your needs. "
        "Key highlights: {features}.",
    ],
    "casual": [
        "Meet the {name} — your new favorite {category}! Packed with {features}, "
        "it's the perfect addition to your daily life.",
        "Looking for an awesome {category}? The {name} is exactly what you need. "
        "Features include {features}.",
        "Say hello to the {name}! This {category} is loaded with {features} and "
        "ready for any occasion.",
    ],
    "marketing": [
        "BEST DEAL: {name} – Exclusive Offer! This premium {category} comes with "
        "{features} — unbeatable value. Limited time!",
        "FLASH SALE: The {name} is flying off the shelves! A top-rated {category} "
        "featuring {features}. Secure yours now!",
        "SPECIAL PROMOTION: Upgrade with the {name}. This {category} includes "
        "{features}. Join thousands of happy customers!",
    ],
}

_GENERATION_PROMPT = """You are an SEO copywriter for SnapTrip, an e-commerce platform.

Generate 3 product descriptions for the following product. Each description should:
- Be 2-4 sentences
- Include the product name naturally
- Highlight key features
- Be optimized for search engines
- Use a {style} tone

Also suggest 5 SEO keywords relevant to this product.

Product Name: {product_name}
Category: {category}
Key Features: {features}

Reply with ONLY a JSON object:
{{
  "suggestions": ["desc1", "desc2", "desc3"],
  "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"]
}}"""


class GenerateProductDescArgs(BaseModel):
    product_name: str = Field(..., description="Product name")
    category: str = Field(
        "general", description="Product category (electronics, clothing, food, etc.)"
    )
    features: str = Field("", description="Key features, comma-separated")
    style: str = Field(
        "professional", description="Writing style: professional, casual, marketing"
    )


class GenerateProductDescTool(SmartDayBaseTool):
    name: str = "generate_product_desc"
    description: str = (
        "Generate SEO-friendly product descriptions and keywords. "
        "Uses LLM to create high-quality, unique copy in the requested style. "
        "Falls back to template-based generation if LLM is unavailable."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GenerateProductDescArgs
    tool_timeout: float = 15.0

    async def _arun(self, **kwargs: Any) -> dict:
        product_name = kwargs.get("product_name", "")
        category = kwargs.get("category", "") or "general"
        features = kwargs.get("features", "") or "premium quality, reliable performance"
        style = kwargs.get("style", "professional")

        # Normalize features
        feature_items = [f.strip() for f in features.split(",") if f.strip()]
        if not feature_items:
            feature_items = ["premium quality", "reliable performance"]
        feature_text = ", ".join(feature_items)

        # Try LLM first
        try:
            from agent.graph import _runtime

            adapter = _runtime.llm_adapter if _runtime else None
            if adapter:
                prompt = _GENERATION_PROMPT.format(
                    style=style,
                    product_name=product_name,
                    category=category,
                    features=feature_text,
                )
                response = await adapter.chat_json(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=1024,
                    timeout_s=12.0,
                )
                if response and response.get("suggestions"):
                    return {
                        "product_name": product_name,
                        "category": category,
                        "style": style,
                        "suggestions": response.get("suggestions", []),
                        "keywords": response.get("keywords", []),
                        "generated_by": "llm",
                    }
        except Exception:
            logger.warning(
                "generate_product_desc: LLM generation failed, using templates",
                exc_info=True,
            )

        # Fallback to templates
        templates = _FALLBACK_TEMPLATES.get(style, _FALLBACK_TEMPLATES["professional"])
        suggestions = [
            tpl.format(name=product_name, category=category, features=feature_text)
            for tpl in templates
        ]
        name_parts = [
            p.strip().lower() for p in product_name.split() if len(p.strip()) > 2
        ]
        keywords = name_parts + [
            f"{category} deal",
            f"best {category}",
            "premium product",
            "online shop",
            "fast delivery",
        ]

        return {
            "product_name": product_name,
            "category": category,
            "style": style,
            "suggestions": suggestions,
            "keywords": keywords[:8],
            "generated_by": "template_fallback",
        }

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
