"""Compare products tool — side-by-side product comparison."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class CompareProductsArgs(BaseModel):
    product_ids: list[str] = Field(
        ..., description="List of product IDs to compare (2-5 recommended)"
    )


class CompareProductsTool(SmartDayBaseTool):
    name: str = "compare_products"
    description: str = (
        "Compare multiple products side by side. "
        "Returns detailed specs, prices, and ratings for each product "
        "so users can make informed purchase decisions."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = CompareProductsArgs
    tool_timeout: float = 8.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            product_ids = kwargs.get("product_ids", [])
            if not product_ids:
                return {"error": "No product IDs provided", "products": []}

            # Limit to 5 products for performance
            product_ids = product_ids[:5]

            hdrs = auth_header()

            # Try batch endpoint first, fall back to individual fetches
            try:
                async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                    response = await client.post(
                        f"{MARKETPLACE_URL}/api/v1/portal/products/batch",
                        json={"ids": product_ids},
                        headers=hdrs,
                    )
                    response.raise_for_status()
                    data = response.json()
                    inner = data.get("data", data)
                    products = inner.get("products", inner.get("items", []))
                    if isinstance(products, list) and products:
                        return self._format_result(product_ids, products)
            except (httpx.HTTPStatusError, httpx.RequestError):
                pass  # Fall back to individual fetches

            # Fallback: fetch each product individually in parallel
            async def fetch_one(pid: str) -> dict[str, Any] | None:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(
                            f"{MARKETPLACE_URL}/api/v1/portal/products/{pid}",
                            headers=hdrs,
                        )
                        resp.raise_for_status()
                        d = resp.json()
                        inner = d.get("data", d)
                        return {
                            "product_id": str(inner.get("id", pid)),
                            "name": inner.get("name", ""),
                            "description": (inner.get("description", "") or "")[:300],
                            "price": inner.get("price", 0),
                            "stock": inner.get("stock", 0),
                            "brand_name": inner.get("brand_name", ""),
                            "category_name": inner.get("category_name", ""),
                            "images": (inner.get("images", []) or [])[:2],
                            "skus": inner.get("skus", []),
                        }
                except Exception:
                    return {"product_id": str(pid), "error": "Failed to fetch"}

            results = await asyncio.gather(*[fetch_one(pid) for pid in product_ids])
            products = [r for r in results if r is not None]
            return self._format_result(product_ids, products)

        except Exception as e:
            return {"error": f"Comparison failed: {str(e)}", "products": []}

    def _format_result(
        self, requested_ids: list[str], products: list[dict[str, Any]]
    ) -> dict:
        """Format comparison results with price range summary."""
        valid = [p for p in products if "error" not in p]
        prices = [p.get("price", 0) for p in valid if p.get("price")]
        return {
            "requested_count": len(requested_ids),
            "found_count": len(valid),
            "price_range": {
                "min": min(prices) if prices else 0,
                "max": max(prices) if prices else 0,
            },
            "products": [
                {
                    "product_id": p.get("product_id", ""),
                    "name": p.get("name", ""),
                    "price": p.get("price", 0),
                    "stock": p.get("stock", 0),
                    "brand_name": p.get("brand_name", ""),
                    "category_name": p.get("category_name", ""),
                    "description": (p.get("description", "") or "")[:200],
                    "images": (p.get("images", []) or [])[:2],
                    "purchase_link": f"https://shop.snaptrip.com/product/{p.get('product_id', '')}",
                }
                for p in products
            ],
        }

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
