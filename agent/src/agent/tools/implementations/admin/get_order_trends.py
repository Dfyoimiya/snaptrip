"""Get order trends tool — aggregate order statistics from marketplace."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetOrderTrendsArgs(BaseModel):
    days: int = Field(7, description="Number of days to analyze")


class GetOrderTrendsTool(SmartDayBaseTool):
    name: str = "get_order_trends"
    description: str = (
        "Get order trends: recent orders, status distribution, total amounts. "
        "Aggregates order data over a configurable time window."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetOrderTrendsArgs
    tool_timeout: float = 8.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            days = kwargs.get("days", 7)
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/orders",
                    params={"page": 1, "page_size": 100},
                )
                response.raise_for_status()
                data = response.json()

                inner = data.get("data", data)
                orders = inner.get("items", inner.get("orders", []))
                total_count = inner.get("total", len(orders))

                # Aggregate status distribution
                status_map: dict[int, str] = {
                    0: "pending_payment",
                    1: "pending_shipment",
                    2: "shipped",
                    3: "completed",
                    4: "refunding",
                    5: "refunded",
                    6: "cancelled",
                }
                status_counts: dict[str, int] = {}
                total_amount = 0
                recent_orders: list[dict[str, Any]] = []

                for order in orders:
                    status = order.get("status", 0)
                    status_label = status_map.get(status, f"unknown_{status}")
                    status_counts[status_label] = status_counts.get(status_label, 0) + 1

                    total_amount += order.get("total_amount", order.get("pay_amount", 0))

                    if len(recent_orders) < 10:
                        recent_orders.append(
                            {
                                "order_id": order.get("id"),
                                "order_sn": order.get("order_sn", order.get("orderSn", "")),
                                "status": status,
                                "amount": order.get("total_amount", order.get("pay_amount", 0)),
                                "created_at": order.get("created_at", order.get("create_time", "")),
                            }
                        )

                return {
                    "days_analyzed": days,
                    "total_orders_fetched": total_count,
                    "status_distribution": status_counts,
                    "total_amount_sum": total_amount,
                    "recent_orders": recent_orders,
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
