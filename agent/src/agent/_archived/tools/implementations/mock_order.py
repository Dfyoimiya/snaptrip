# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 ARCHIVED — TRIP PLANNING AGENT                      ║
# ║  Archived: 2026-06-07                                                        ║
# ║  Reason: Agent repurposed from local trip planning to new domain             ║
# ║  This file is preserved for reference but NOT imported by the framework.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

"""MockOrderTool — restaurant reservations, activity tickets, delivery orders.

Mutable tool: creates orders that can be compensated (cancelled) on rollback.
Simulates ~5% failure for realistic rollback testing.
"""

from __future__ import annotations

import random
import time as _time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

_MOCK_ORDERS: dict[str, dict[str, Any]] = {}


class OrderInput(BaseModel):
    """Input schema for mock order creation."""

    order_type: str = Field(default="", description="restaurant/activity/cake/flowers/wechat")
    poi_id: str = Field(default="", description="POI/restaurant/activity ID")
    guest_count: int = Field(default=1, ge=1, le=20)
    child_count: int = Field(default=0, ge=0, le=10)
    time: str = Field(default="", description="Reservation time, e.g. '18:00'")
    reserve_only: bool = Field(default=False, description="Phase 1: soft-reserve")
    item_type: str = Field(default="", description="For delivery: cake/flowers")
    delivery_time: str = Field(default="", description="Expected delivery time")
    user_id: str = Field(default="", description="User ID (for wechat)")
    message: str = Field(default="", description="Message text (for wechat)")
    recipient: str = Field(default="", description="Recipient (for wechat)")


class MockOrderTool(SmartDayBaseTool):
    """Create restaurant reservations, activity tickets, delivery orders, and notifications.

    Contract:
      - mutable: creates orders in mock DB
      - compensation: cancel_order (idempotent, sets status=CANCELLED)
      - failure rate: ~5%
    """

    name: str = "mock_order_create"
    description: str = (
        "Create a restaurant table reservation, activity ticket order, cake/flowers "
        "delivery order, or send a WeChat notification. "
        "Use this during the execution phase AFTER the user has confirmed the itinerary "
        "— never during planning or search."
    )
    args_schema: type[BaseModel] = OrderInput
    is_read_only: bool = False
    cost_model: str = "mock"
    tool_timeout: float = 10.0

    async def _arun(
        self,
        order_type: str = "",
        poi_id: str = "",
        guest_count: int = 1,
        child_count: int = 0,
        time: str = "",
        reserve_only: bool = False,
        item_type: str = "",
        delivery_time: str = "",
        user_id: str = "",
        message: str = "",
        recipient: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        # ~5% simulated failure
        if random.random() < 0.05:
            return ToolResult(success=False, data={"error": "Mock order service temporarily unavailable"})

        if order_type == "wechat":
            return ToolResult(
                success=True,
                data={"sent": True, "recipient": recipient or "家人"},
                idempotency_key=f"wechat:{user_id}:{_time.time()}",
            )

        prefix = {"restaurant": "bk-rst", "activity": "bk-act", "cake": "ord-cake", "flowers": "ord-flw"}
        order_id = f"{prefix.get(order_type, 'ord')}-{uuid.uuid4().hex[:8].upper()}"

        cost_map = {"restaurant": 68.0, "activity": 120.0, "cake": 199.0, "flowers": 128.0}
        base = cost_map.get(order_type, 50.0)
        total_cost = round(base * (guest_count + child_count * 0.5), 2)
        status = "reserved" if reserve_only else "confirmed"

        _MOCK_ORDERS[order_id] = {
            "order_id": order_id, "order_type": order_type, "poi_id": poi_id,
            "guest_count": guest_count, "child_count": child_count,
            "time": time, "status": status, "cost_cny": total_cost,
        }

        return ToolResult(
            success=True,
            data={
                "order_id": order_id, "booking_id": order_id,
                "poi_id": poi_id, "guest_count": guest_count,
                "child_count": child_count, "time": time,
                "status": status, "total_price": int(total_cost), "cost_cny": total_cost,
            },
            cost_cny=total_cost,
            idempotency_key=f"order:{order_type}:{poi_id}:{time}:{guest_count}",
        )

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        order_id = result.data.get("order_id") or result.data.get("booking_id", "")
        return CompensationAction(
            action_id=f"cancel_order:{order_id}",
            tool_name=self.name,
            description=f"Cancel order {order_id} ({args.get('order_type', 'unknown')})",
            execute=self._cancel_order(order_id),
            max_retries=3,
        )

    @staticmethod
    def _cancel_order(order_id: str):
        async def _cancel() -> None:
            if order_id in _MOCK_ORDERS:
                _MOCK_ORDERS[order_id]["status"] = "CANCELLED"
        return _cancel
