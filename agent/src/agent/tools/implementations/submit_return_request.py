"""Submit return request tool — create a return/refund application (write, Saga)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

logger = logging.getLogger(__name__)

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class SubmitReturnRequestArgs(BaseModel):
    order_id: str = Field(..., description="Order ID to submit return for")
    reason: str = Field(..., description="Reason for return")
    description: str | None = Field(None, description="Additional description of the issue")
    product_count: int = Field(default=1, description="Number of items to return")


class SubmitReturnRequestTool(SmartDayBaseTool):
    name: str = "submit_return_request"
    description: str = (
        "Submit a return/refund request for an order. "
        "ONLY use after confirming eligibility via check_return_eligibility. "
        "Returns the return application ID and status."
    )
    is_read_only: bool = False
    cost_model: str = "free"
    args_schema: type[BaseModel] = SubmitReturnRequestArgs
    tool_timeout: float = 10.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            order_id = kwargs["order_id"]
            payload: dict[str, Any] = {
                "order_id": order_id,
                "reason": kwargs.get("reason", ""),
                "description": kwargs.get("description"),
                "product_count": kwargs.get("product_count", 1),
            }
            hdrs = auth_header()
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.post(
                    f"{MARKETPLACE_URL}/api/v1/portal/cs/orders/{order_id}/return",
                    json=payload,
                    headers=hdrs,
                )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        """Return applications are irreversible — manual admin intervention required."""
        order_id = args.get("order_id", "unknown")

        async def _return_rollback() -> None:
            logger.warning(
                "SubmitReturn compensation: return for order %s is irreversible. "
                "Admin must manually reject the return application.",
                order_id,
            )

        return CompensationAction(
            action_id=self._idem_key(args),
            tool_name=self.name,
            description=f"Return-request rollback for order {order_id} (no-op: requires manual admin action)",
            execute=_return_rollback,
        )
