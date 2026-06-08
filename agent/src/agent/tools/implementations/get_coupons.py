"""Get coupons tool — retrieve available or user-claimed coupons."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetCouponsArgs(BaseModel):
    mode: str = Field("available", description="'available' for all available coupons, 'mine' for user's coupons")
    use_status: int | None = Field(None, description="For 'mine': 0=unused, 1=used, 2=expired")


class GetCouponsTool(SmartDayBaseTool):
    name: str = "get_coupons"
    description: str = "Get available coupons or user's claimed coupons"
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetCouponsArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            mode = kwargs.get("mode", "available")
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                if mode == "mine":
                    params: dict[str, Any] = {}
                    if kwargs.get("use_status") is not None:
                        params["use_status"] = kwargs["use_status"]
                    response = await client.get(
                        f"{MARKETPLACE_URL}/api/v1/portal/coupons/mine",
                        params=params or None,
                    )
                else:
                    response = await client.get(
                        f"{MARKETPLACE_URL}/api/v1/portal/coupons/available",
                    )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
