"""Get sales report tool — fetch dashboard snapshot + daily sales trend."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetSalesReportArgs(BaseModel):
    days: int = Field(
        7, description="Number of days to analyze (1=today, 7=week, 30=month)"
    )


class GetSalesReportTool(SmartDayBaseTool):
    name: str = "get_sales_report"
    description: str = (
        "Get sales report with dashboard snapshot (today's revenue, orders, "
        "pending returns, new members, order status breakdown) AND daily sales "
        "trend over the requested number of days. Returns both snapshot and trend."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetSalesReportArgs
    tool_timeout: float = 8.0

    async def _arun(self, **kwargs: Any) -> dict:
        days = kwargs.get("days", 7)
        hdrs = auth_header()
        try:
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                # 1. Dashboard snapshot (today's key metrics)
                dash_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/dashboard",
                    headers=hdrs,
                )
                dash_resp.raise_for_status()
                dash_data = dash_resp.json()
                dash_inner = dash_data.get("data", dash_data)

                # 2. Overview stats (total products, on-shelf count)
                overview_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/stats/overview",
                    headers=hdrs,
                )
                overview_resp.raise_for_status()
                overview_data = overview_resp.json()
                overview_inner = overview_data.get("data", overview_data)

                # 3. Daily sales trend
                sales_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/stats/sales",
                    params={"days": days},
                    headers=hdrs,
                )
                sales_resp.raise_for_status()
                sales_data = sales_resp.json()
                daily_trend = sales_data.get("data", [])

                # 4. Product ranking (top 5)
                rank_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/stats/products",
                    params={"limit": 5},
                    headers=hdrs,
                )
                rank_resp.raise_for_status()
                rank_data = rank_resp.json()
                top_products = rank_data.get("data", [])

                return {
                    # Snapshot
                    "today_orders": dash_inner.get("today_orders", 0),
                    "today_revenue": dash_inner.get("today_revenue", 0),
                    "today_revenue_display": dash_inner.get(
                        "today_revenue_display", "¥0"
                    ),
                    "pending_returns": dash_inner.get("pending_returns", 0),
                    "new_members": dash_inner.get("new_members", 0),
                    "order_status_counts": dash_inner.get("order_status_counts", []),
                    # Overview
                    "total_products": overview_inner.get("total_product_count", 0),
                    "on_shelf_products": overview_inner.get(
                        "on_shelf_product_count", 0
                    ),
                    # Trend
                    "days_requested": days,
                    "daily_sales_trend": [
                        {
                            "date": item.get("date", ""),
                            "order_count": item.get("order_count", 0),
                            "amount": item.get("amount", 0),
                        }
                        for item in daily_trend
                    ],
                    # Top products
                    "top_products": [
                        {
                            "product_id": p.get("product_id", ""),
                            "product_name": p.get("product_name", ""),
                            "sale_count": p.get("sale_count", 0),
                            "amount": p.get("amount", 0),
                        }
                        for p in top_products
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
