"""Cancel order tool — cancel an unpaid order (write operation, needs Saga)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

logger = logging.getLogger(__name__)

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class CancelOrderArgs(BaseModel):
    order_id: str = Field(..., description="Order ID to cancel")
    reason: str = Field("用户取消", description="Cancellation reason")


class CancelOrderTool(SmartDayBaseTool):
    name: str = "cancel_order"
    description: str = "Cancel an unpaid order"
    is_read_only: bool = False
    cost_model: str = "free"
    args_schema: type[BaseModel] = CancelOrderArgs
    tool_timeout: float = 10.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            order_id = kwargs["order_id"]
            payload: dict[str, Any] = {"reason": kwargs.get("reason", "用户取消")}

            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                # Try portal cancel endpoint first, fall back to admin close
                try:
                    response = await client.post(
                        f"{MARKETPLACE_URL}/api/v1/portal/orders/{order_id}/cancel",
                        json=payload,
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    # Fallback: try admin close endpoint
                    if e.response.status_code == 404:
                        response = await client.post(
                            f"{MARKETPLACE_URL}/api/v1/admin/orders/{order_id}/close",
                            json=payload,
                        )
                        response.raise_for_status()
                    else:
                        raise
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        """Cancellation is inherently irreversible — order state cannot be un-cancelled.

        The compensation is a no-op that logs a warning. Manual intervention
        (re-creating the order) would be required to truly reverse a cancel.
        """
        order_id = args.get("order_id", "unknown")

        async def _cancel_rollback() -> None:
            logger.warning(
                "CancelOrder compensation: order %s cancellation is irreversible. "
                "Manual re-creation required.",
                order_id,
            )

        return CompensationAction(
            action_id=self._idem_key(args),
            tool_name=self.name,
            description=f"Cancel-order rollback for order {order_id} (no-op: cancellation is irreversible)",
            execute=_cancel_rollback,
        )
