"""Get sales report tool — fetch dashboard analytics from marketplace."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetSalesReportArgs(BaseModel):
    days: int = Field(1, description="Number of days to report (1=today, 7=week)")


class GetSalesReportTool(SmartDayBaseTool):
    name: str = "get_sales_report"
    description: str = (
        "Get sales report: today's revenue, today's orders, pending returns, "
        "and order status breakdown. Returns dashboard-level aggregations."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetSalesReportArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/dashboard",
                )
                response.raise_for_status()
                data = response.json()

                # Extract the "data" wrapper from the success response
                inner = data.get("data", data)
                return {
                    "today_revenue": inner.get("today_revenue", 0),
                    "today_revenue_display": inner.get("today_revenue_display", "¥0"),
                    "today_orders": inner.get("today_orders", 0),
                    "pending_returns": inner.get("pending_returns", 0),
                    "new_members": inner.get("new_members", 0),
                    "order_status_counts": inner.get("order_status_counts", []),
                    "days_requested": kwargs.get("days", 1),
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
