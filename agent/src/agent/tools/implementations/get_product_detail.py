"""Get product detail tool — fetch full information about a specific product."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetProductDetailArgs(BaseModel):
    product_id: str = Field(..., description="Product ID")


class GetProductDetailTool(SmartDayBaseTool):
    name: str = "get_product_detail"
    description: str = "Get detailed information about a specific product including name, description, price, stock, SKUs, and images"
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetProductDetailArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            product_id = kwargs["product_id"]
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/portal/products/{product_id}",
                )
                response.raise_for_status()
                data = response.json()

                # Extract key fields for agent-friendly output
                result: dict[str, Any] = {}
                if isinstance(data, dict):
                    product = data.get("data", data)
                    result["product_id"] = product.get("id", product.get("product_id", ""))
                    result["name"] = product.get("name", "")
                    result["description"] = product.get("description", "")
                    result["price"] = product.get("price", 0)
                    result["stock"] = product.get("stock", 0)
                    result["skus"] = product.get("skus", [])
                    result["images"] = product.get("images", [])
                    result["category_id"] = product.get("category_id", "")
                    result["category_name"] = product.get("category_name", "")
                    # Include raw data for downstream use
                    result["_raw"] = product
                else:
                    result = data
                return result
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
