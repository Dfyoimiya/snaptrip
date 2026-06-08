"""Get low stock alert tool — identify products below inventory threshold."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetLowStockAlertArgs(BaseModel):
    threshold: int = Field(20, description="Stock threshold (default 20)")


class GetLowStockAlertTool(SmartDayBaseTool):
    name: str = "get_low_stock_alert"
    description: str = (
        "Get list of products with low stock (below threshold). "
        "Returns product name, SKU, current stock, and alert severity."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetLowStockAlertArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            threshold = kwargs.get("threshold", 20)
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/products",
                    params={"publish_status": 1, "page_size": 100},
                )
                response.raise_for_status()
                data = response.json()

                # Extract the "data" wrapper; products list is within
                inner = data.get("data", data)
                products = inner.get("items", inner.get("products", []))

                # Filter client-side by stock threshold
                low_stock: list[dict[str, Any]] = []
                for product in products:
                    stock = product.get("stock", 0)
                    if stock < threshold:
                        low_stock.append(
                            {
                                "product_id": product.get("id"),
                                "product_name": product.get("name", ""),
                                "stock": stock,
                                "threshold": threshold,
                                "sku_code": product.get("sku_code", ""),
                            }
                        )

                return {
                    "threshold": threshold,
                    "low_stock_count": len(low_stock),
                    "low_stock_products": low_stock,
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
