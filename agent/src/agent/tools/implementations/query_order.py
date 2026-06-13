"""Query order tool — look up order status by ID or list user orders."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class QueryOrderArgs(BaseModel):
    order_id: str | None = Field(None, description="Specific order ID to query")
    status: int | None = Field(
        None, description="Filter by status: 0=pending, 1=paid, 2=shipped, 3=received"
    )
    page: int = Field(1, description="Page number")


class QueryOrderTool(SmartDayBaseTool):
    name: str = "query_order"
    description: str = (
        "Query order status by order ID or list user's orders filtered by status"
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = QueryOrderArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            hdrs = auth_header()
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                if kwargs.get("order_id"):
                    # Query specific order
                    response = await client.get(
                        f"{MARKETPLACE_URL}/api/v1/portal/orders/{kwargs['order_id']}",
                        headers=hdrs,
                    )
                else:
                    # List orders with optional status filter
                    params: dict[str, Any] = {"page": kwargs.get("page", 1)}
                    if kwargs.get("status") is not None:
                        params["status"] = kwargs["status"]
                    response = await client.get(
                        f"{MARKETPLACE_URL}/api/v1/portal/orders",
                        params=params,
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
