"""Get recommendations tool — personalized product recommendations."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetRecommendationsArgs(BaseModel):
    scene: str = Field(
        "homepage",
        description="Recommendation scene: homepage, product_detail, cart",
    )
    max_results: int = Field(
        5, description="Maximum results to return (default 5, max 20)"
    )


class GetRecommendationsTool(SmartDayBaseTool):
    name: str = "get_recommendations"
    description: str = (
        "Get personalized product recommendations including 'Guess You Like', "
        "trending items, and new arrivals based on user behavior and preferences."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetRecommendationsArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            scene = kwargs.get("scene", "homepage")
            max_results = min(int(kwargs.get("max_results", 5)), 20)
            hdrs = auth_header()

            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.post(
                    f"{MARKETPLACE_URL}/api/v1/portal/recommendations",
                    json={"scene": scene, "num_items": max_results},
                    headers=hdrs,
                )
                response.raise_for_status()
                data = response.json()

            # Unwrap success() wrapper
            inner = data.get("data", data)
            products = inner.get("products", [])

            return {
                "scene": scene,
                "total": len(products),
                "experiment_group": inner.get("experiment_group", "control"),
                "products": [
                    {
                        "product_id": p.get("product_id", ""),
                        "name": p.get("name", ""),
                        "price": p.get("price", 0),
                        "brand_name": p.get("brand_name", ""),
                        "image_url": p.get("image_url", ""),
                        "sale_count": p.get("sale_count", 0),
                        "stock": p.get("stock", 0),
                        "score": p.get("score", 0),
                        "marketing_copy": p.get("marketing_copy", ""),
                    }
                    for p in products
                ],
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
