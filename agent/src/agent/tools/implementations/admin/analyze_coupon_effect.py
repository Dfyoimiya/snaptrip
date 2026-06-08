"""Analyze coupon effect tool — compute coupon usage and effectiveness stats."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class AnalyzeCouponEffectArgs(BaseModel):
    coupon_id: str | None = Field(None, description="Specific coupon ID, or None for all")


class AnalyzeCouponEffectTool(SmartDayBaseTool):
    name: str = "analyze_coupon_effect"
    description: str = (
        "Analyze coupon effectiveness: usage count, conversion rate, discount totals. "
        "Works for a specific coupon or all coupons."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = AnalyzeCouponEffectArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            coupon_id = kwargs.get("coupon_id")
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                if coupon_id:
                    # Fetch specific coupon detail
                    response = await client.get(
                        f"{MARKETPLACE_URL}/api/v1/admin/coupons/{coupon_id}",
                    )
                    response.raise_for_status()
                    data = response.json()
                    inner = data.get("data", data)
                    coupon = inner if isinstance(inner, dict) else {}

                    return {
                        "coupon_id": coupon.get("id", coupon_id),
                        "coupon_name": coupon.get("name", ""),
                        "type": coupon.get("type"),
                        "amount": coupon.get("amount", coupon.get("discount", 0)),
                        "min_point": coupon.get("min_point", coupon.get("min_amount", 0)),
                        "used_count": coupon.get("used_count", coupon.get("use_count", 0)),
                        "total_count": coupon.get("total_count", coupon.get("count", 0)),
                        "status": coupon.get("status"),
                        "start_time": coupon.get("start_time", ""),
                        "end_time": coupon.get("end_time", ""),
                        "usage_rate": (
                            round(coupon.get("used_count", 0) / max(coupon.get("total_count", 1), 1), 4)
                            if coupon.get("total_count")
                            else 0
                        ),
                    }

                # Fetch all coupons
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/coupons",
                    params={"page": 1, "page_size": 100},
                )
                response.raise_for_status()
                data = response.json()

                inner = data.get("data", data)
                coupons = inner.get("items", inner.get("coupons", []))

                total_used = 0
                total_issued = 0
                coupon_stats: list[dict[str, Any]] = []

                for c in coupons:
                    used = c.get("used_count", c.get("use_count", 0))
                    issued = c.get("total_count", c.get("count", 0))
                    total_used += used
                    total_issued += issued

                    coupon_stats.append(
                        {
                            "coupon_id": c.get("id"),
                            "coupon_name": c.get("name", ""),
                            "type": c.get("type"),
                            "used": used,
                            "issued": issued,
                            "usage_rate": round(used / max(issued, 1), 4) if issued else 0,
                            "status": c.get("status"),
                        }
                    )

                return {
                    "total_coupons": len(coupons),
                    "total_used": total_used,
                    "total_issued": total_issued,
                    "overall_usage_rate": round(total_used / max(total_issued, 1), 4) if total_issued else 0,
                    "coupon_stats": coupon_stats,
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
