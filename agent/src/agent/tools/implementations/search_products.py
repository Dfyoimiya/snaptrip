"""Search products tool — query the marketplace product catalog."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class SearchProductsArgs(BaseModel):
    keyword: str = Field(..., description="Search keyword")
    category_id: str | None = Field(None, description="Optional category filter")
    min_price: float | None = Field(None, description="Minimum price")
    max_price: float | None = Field(None, description="Maximum price")
    page: int = Field(1, description="Page number")
    page_size: int = Field(10, description="Page size")
    sort: str = Field("default", description="Sort order: default, price_asc, price_desc, sales")


class SearchProductsTool(SmartDayBaseTool):
    name: str = "search_products"
    description: str = "Search for products by keyword, category, price range"
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = SearchProductsArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            params: dict[str, Any] = {"keyword": kwargs["keyword"], "page": kwargs.get("page", 1), "page_size": kwargs.get("page_size", 10), "sort": kwargs.get("sort", "default")}
            if kwargs.get("category_id"):
                params["category_id"] = kwargs["category_id"]
            if kwargs.get("min_price") is not None:
                params["min_price"] = kwargs["min_price"]
            if kwargs.get("max_price") is not None:
                params["max_price"] = kwargs["max_price"]

            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/portal/products",
                    params=params,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
