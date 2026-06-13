"""Get order trends tool — use stats endpoints for real trend data."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetOrderTrendsArgs(BaseModel):
    days: int = Field(7, description="Number of days to analyze (default 7, max 365)")


class GetOrderTrendsTool(SmartDayBaseTool):
    name: str = "get_order_trends"
    description: str = (
        "Get order trends using real daily-aggregated sales statistics. "
        "Returns daily order count and revenue over the requested time window, "
        "plus order status distribution from the latest orders snapshot."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetOrderTrendsArgs
    tool_timeout: float = 8.0

    async def _arun(self, **kwargs: Any) -> dict:
        days = kwargs.get("days", 7)
        hdrs = auth_header()
        try:
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                # 1. Daily sales trend (server-side aggregation by DATE)
                sales_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/stats/sales",
                    params={"days": days},
                    headers=hdrs,
                )
                sales_resp.raise_for_status()
                sales_data = sales_resp.json()
                daily_items = sales_data.get("data", [])

                # 2. Dashboard for current order status distribution
                dash_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/dashboard",
                    headers=hdrs,
                )
                dash_resp.raise_for_status()
                dash_data = dash_resp.json()
                dash_inner = dash_data.get("data", dash_data)

                # Compute trend summary
                total_orders = sum(item.get("order_count", 0) for item in daily_items)
                total_revenue = sum(item.get("amount", 0) for item in daily_items)
                avg_daily_orders = round(total_orders / max(len(daily_items), 1), 1)
                avg_daily_revenue = round(total_revenue / max(len(daily_items), 1), 2)

                # Direction: compare first half vs second half
                mid = len(daily_items) // 2
                first_half_rev = sum(
                    item.get("amount", 0) for item in daily_items[:mid]
                )
                second_half_rev = sum(
                    item.get("amount", 0) for item in daily_items[mid:]
                )
                if first_half_rev > 0:
                    trend_direction = (
                        "up"
                        if second_half_rev > first_half_rev
                        else "down"
                        if second_half_rev < first_half_rev
                        else "flat"
                    )
                else:
                    trend_direction = "flat"

                return {
                    "days_analyzed": days,
                    "total_orders": total_orders,
                    "total_revenue": total_revenue,
                    "avg_daily_orders": avg_daily_orders,
                    "avg_daily_revenue": avg_daily_revenue,
                    "trend_direction": trend_direction,
                    "daily_breakdown": [
                        {
                            "date": item.get("date", ""),
                            "orders": item.get("order_count", 0),
                            "revenue": item.get("amount", 0),
                        }
                        for item in daily_items
                    ],
                    "current_status_distribution": dash_inner.get(
                        "order_status_counts", []
                    ),
                    "today_orders": dash_inner.get("today_orders", 0),
                    "today_revenue": dash_inner.get("today_revenue", 0),
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
