"""Get home feed tool — curated homepage recommendation sections."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetHomeFeedArgs(BaseModel):
    """No required args — fetches the full homepage feed."""


class GetHomeFeedTool(SmartDayBaseTool):
    name: str = "get_home_feed"
    description: str = (
        "Get the homepage feed with multiple recommendation sections: "
        "Guess You Like, Trending Now, New Arrivals, Recently Viewed, "
        "and Search Discovery. Each section contains curated products."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetHomeFeedArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            hdrs = auth_header()

            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/portal/home/feed",
                    headers=hdrs,
                )
                response.raise_for_status()
                data = response.json()

            # Unwrap success() wrapper
            inner = data.get("data", data)
            sections = inner.get("sections", inner) if isinstance(inner, dict) else []

            # Normalize sections to a clean format
            result_sections: list[dict[str, Any]] = []
            total_products = 0
            if isinstance(sections, list):
                for section in sections:
                    section_type = section.get("type", section.get("section_type", ""))
                    title = section.get("title", "")
                    products = section.get("products", section.get("items", []))
                    normalized_products = [
                        {
                            "product_id": p.get("product_id", p.get("id", "")),
                            "name": p.get("name", ""),
                            "price": p.get("price", 0),
                            "image_url": p.get("image_url", p.get("defaultPic", "")),
                            "brand_name": p.get("brand_name", ""),
                            "sale_count": p.get("sale_count", p.get("saleCount", 0)),
                        }
                        for p in products
                    ]
                    result_sections.append({
                        "type": section_type,
                        "title": title,
                        "count": len(normalized_products),
                        "products": normalized_products,
                    })
                    total_products += len(normalized_products)

            return {
                "total_sections": len(result_sections),
                "total_products": total_products,
                "sections": result_sections,
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
