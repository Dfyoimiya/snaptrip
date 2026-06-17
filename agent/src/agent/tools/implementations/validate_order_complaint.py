"""Validate order complaint tool — assess if a complaint is justified."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class ValidateOrderComplaintArgs(BaseModel):
    order_id: str = Field(..., description="Order ID to validate complaint for")


class ValidateOrderComplaintTool(SmartDayBaseTool):
    name: str = "validate_order_complaint"
    description: str = (
        "Validate whether a customer complaint about an order is justified. "
        "Checks order existence, ownership, status, and previous complaint history. "
        "Returns validation result and suggested action."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = ValidateOrderComplaintArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            order_id = kwargs["order_id"]
            hdrs = auth_header()
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/portal/cs/orders/{order_id}/validate-complaint",
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
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
