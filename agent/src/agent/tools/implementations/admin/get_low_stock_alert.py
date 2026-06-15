"""Get low stock alert tool — paginate through all products to find low stock."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")

# Page size when iterating through all products
_SCAN_PAGE_SIZE = 50
# Safety cap — don't scan more than this many products
_MAX_PRODUCTS_TO_SCAN = 500


class GetLowStockAlertArgs(BaseModel):
    threshold: int = Field(
        20, description="Stock threshold — products below this count are flagged"
    )
    publish_status: int = Field(
        1, description="Filter: 1=on-shelf only, 0=off-shelf, omit for all"
    )


class GetLowStockAlertTool(SmartDayBaseTool):
    name: str = "get_low_stock_alert"
    description: str = (
        "Get list of products with low stock (below threshold). "
        "Paginates through ALL products up to a safety cap, filters by stock level "
        "server-side where possible. Returns product name, stock, SKU code, "
        "price, and alert severity (critical < 5, warning < threshold)."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetLowStockAlertArgs
    tool_timeout: float = 10.0

    async def _arun(self, **kwargs: Any) -> dict:
        threshold = kwargs.get("threshold", 20)
        publish_status = kwargs.get("publish_status", 1)
        hdrs = auth_header()

        try:
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                low_stock: list[dict[str, Any]] = []
                total_scanned = 0

                page = 1
                while total_scanned < _MAX_PRODUCTS_TO_SCAN:
                    params: dict[str, Any] = {
                        "page": page,
                        "page_size": _SCAN_PAGE_SIZE,
                    }
                    if publish_status is not None:
                        params["publish_status"] = publish_status

                    response = await client.get(
                        f"{MARKETPLACE_URL}/api/v1/admin/products",
                        params=params,
                        headers=hdrs,
                    )
                    response.raise_for_status()
                    data = response.json()
                    inner = data.get("data", data)
                    products = inner.get("items", inner.get("products", []))
                    total = inner.get("total", 0)

                    if not products:
                        break

                    total_scanned += len(products)

                    for product in products:
                        stock = product.get("stock", 0)
                        if stock < threshold:
                            severity = "critical" if stock < 5 else "warning"
                            low_stock.append(
                                {
                                    "product_id": product.get("id", ""),
                                    "product_name": product.get("name", ""),
                                    "product_sn": product.get("product_sn", ""),
                                    "stock": stock,
                                    "price": product.get("price", 0),
                                    "sku_code": product.get("sku_code", ""),
                                    "severity": severity,
                                }
                            )

                    # Stop if we've fetched all pages
                    if page * _SCAN_PAGE_SIZE >= total:
                        break
                    page += 1

                # Sort: critical first, then by stock ascending
                low_stock.sort(
                    key=lambda x: (0 if x["severity"] == "critical" else 1, x["stock"])
                )

                return {
                    "threshold": threshold,
                    "total_products_scanned": total_scanned,
                    "low_stock_count": len(low_stock),
                    "critical_count": sum(
                        1 for p in low_stock if p["severity"] == "critical"
                    ),
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
