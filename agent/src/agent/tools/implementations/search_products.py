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
    query: str = Field(
        ..., description="Natural language search query describing what the user wants"
    )
    category: str | None = Field(
        None, description="Product category: hotel, flight, tour, package, all"
    )
    max_results: int = Field(
        5, description="Maximum results to return (default 5, max 20)"
    )
    sort_by: str = Field(
        "default", description="Sort order: default, sales, new, price_asc, price_desc"
    )
    page: int = Field(1, description="Page number")
    page_size: int = Field(10, description="Page size")
    min_price: float | None = Field(None, description="Minimum price filter")
    max_price: float | None = Field(None, description="Maximum price filter")


class SearchProductsTool(SmartDayBaseTool):
    name: str = "search_products"
    description: str = (
        "Search the product catalog for travel products matching user criteria. "
        "Uses keyword search across hotels, flights, tours, and packages. "
        "Returns ranked list of matching products with prices and descriptions."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = SearchProductsArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            # Accept both 'query' (from LLM function calling) and 'keyword' (legacy)
            keyword = kwargs.get("query") or kwargs.get("keyword", "")
            category = kwargs.get("category")
            sort_by = kwargs.get("sort_by", "default")
            page = kwargs.get("page", 1)
            page_size = min(
                kwargs.get("page_size", 10), int(kwargs.get("max_results", 20))
            )

            # Map 'all' -> None (no category filter)
            if category and category.lower() == "all":
                category = None

            params: dict[str, Any] = {
                "keyword": keyword,
                "page": page,
                "page_size": page_size,
                "sort_by": sort_by,
            }
            if category:
                params["category_id"] = category  # portal API uses category_id
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
                data = response.json()

            # Unwrap success() wrapper and PaginatedResponse
            inner = data.get("data", data)
            items = inner.get("items", [])
            total = inner.get("total", len(items))

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "products": [
                    {
                        "product_id": p.get("id", ""),
                        "name": p.get("name", ""),
                        "description": (p.get("description", "") or "")[:200],
                        "price": p.get("price", 0),
                        "stock": p.get("stock", 0),
                        "category_name": p.get("category_name", ""),
                        "brand_name": p.get("brand_name", ""),
                        "sale_count": p.get("sale_count", 0),
                        "images": (p.get("images", []) or [])[:3],
                    }
                    for p in items
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
