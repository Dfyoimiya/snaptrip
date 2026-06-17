"""Get coupons tool — retrieve available or user-claimed coupons."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetCouponsArgs(BaseModel):
    category: str = Field(
        "all",
        description="Filter by product category: electronics, clothing, food, home, all",
    )
    min_discount: float | None = Field(
        None, description="Minimum discount percentage filter (e.g., 10 for 10% off)"
    )
    mode: str = Field(
        "available",
        description="'available' for all available coupons, 'mine' for user's claimed coupons",
    )
    use_status: int | None = Field(
        None, description="For 'mine' mode: 0=unused, 1=used, 2=expired"
    )


class GetCouponsTool(SmartDayBaseTool):
    name: str = "get_coupons"
    description: str = (
        "Get available coupons and discount codes. Returns active coupons with "
        "discount amount, minimum spend, validity dates, and applicable categories. "
        "Can also retrieve the current user's claimed coupons with usage status."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetCouponsArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            mode = kwargs.get("mode", "available")
            min_discount = kwargs.get("min_discount")
            hdrs = auth_header()

            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                if mode == "mine":
                    params: dict[str, Any] = {}
                    if kwargs.get("use_status") is not None:
                        params["use_status"] = kwargs["use_status"]
                    response = await client.get(
                        f"{MARKETPLACE_URL}/api/v1/portal/coupons/mine",
                        params=params or None,
                        headers=hdrs,
                    )
                else:
                    response = await client.get(
                        f"{MARKETPLACE_URL}/api/v1/portal/coupons/available",
                        headers=hdrs,
                    )
                response.raise_for_status()
                data = response.json()

            # Unwrap success() wrapper
            inner = data.get("data", data)
            coupons = inner.get("items", inner) if isinstance(inner, dict) else inner
            if not isinstance(coupons, list):
                coupons = [coupons] if coupons else []

            # Apply min_discount filter client-side if specified
            if min_discount is not None:
                filtered: list[dict[str, Any]] = []
                for c in coupons:
                    amount = c.get("amount", c.get("discount", 0))
                    min_point = c.get("min_point", c.get("min_amount", 0))
                    if min_point > 0 and (amount / min_point * 100) >= min_discount:
                        filtered.append(c)
                    elif amount >= min_discount:  # fixed-amount coupon
                        filtered.append(c)
                coupons = filtered

            return {
                "mode": mode,
                "total": len(coupons),
                "coupons": [
                    {
                        "coupon_id": c.get("id", ""),
                        "name": c.get("name", ""),
                        "type": c.get("type"),
                        "amount": c.get("amount", c.get("discount", 0)),
                        "min_point": c.get("min_point", c.get("min_amount", 0)),
                        "start_time": c.get("start_time", ""),
                        "end_time": c.get("end_time", ""),
                        "status": c.get("status"),
                        "use_status": c.get("use_status"),
                    }
                    for c in coupons
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
