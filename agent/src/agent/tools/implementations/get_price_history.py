"""Get price history tool — track product price changes over time."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetPriceHistoryArgs(BaseModel):
    product_id: str = Field(..., description="Product ID")


class GetPriceHistoryTool(SmartDayBaseTool):
    name: str = "get_price_history"
    description: str = (
        "Get price history and discount information for a product. "
        "Returns current price, original price, discount percentage, "
        "and recent price changes so users can decide if it's a good time to buy."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetPriceHistoryArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            product_id = kwargs["product_id"]
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/portal/products/{product_id}/price-history",
                )
                response.raise_for_status()
                data = response.json()

            inner = data.get("data", data)
            return inner if isinstance(inner, dict) else data
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
