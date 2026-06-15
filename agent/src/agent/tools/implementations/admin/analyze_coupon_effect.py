"""Analyze coupon effect tool — usage stats, conversion rates, and history."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class AnalyzeCouponEffectArgs(BaseModel):
    coupon_id: str | None = Field(
        None,
        description="Specific coupon ID to analyze, or omit for all-coupons overview",
    )


class AnalyzeCouponEffectTool(SmartDayBaseTool):
    name: str = "analyze_coupon_effect"
    description: str = (
        "Analyze coupon effectiveness: usage count, conversion rate, discount totals, "
        "and recent claim/use history. Works for a specific coupon or all coupons."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = AnalyzeCouponEffectArgs
    tool_timeout: float = 8.0

    async def _arun(self, **kwargs: Any) -> dict:
        coupon_id = kwargs.get("coupon_id")
        hdrs = auth_header()
        try:
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                if coupon_id:
                    return await self._analyze_single(client, coupon_id, hdrs)
                else:
                    return await self._analyze_all(client, hdrs)
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    async def _analyze_single(
        self, client: httpx.AsyncClient, coupon_id: str, hdrs: dict[str, str]
    ) -> dict:
        # Fetch coupon detail
        resp = await client.get(
            f"{MARKETPLACE_URL}/api/v1/admin/coupons/{coupon_id}",
            headers=hdrs,
        )
        resp.raise_for_status()
        data = resp.json()
        inner = data.get("data", data)
        coupon = inner if isinstance(inner, dict) else {}

        # Fetch coupon histories (claim and usage records)
        history_resp = await client.get(
            f"{MARKETPLACE_URL}/api/v1/admin/coupons/{coupon_id}/histories",
            params={"page": 1, "page_size": 50},
            headers=hdrs,
        )
        history_resp.raise_for_status()
        history_data = history_resp.json()
        history_inner = history_data.get("data", history_data)
        histories = history_inner.get("items", [])
        total_history = history_inner.get("total", len(histories))

        used_count = coupon.get("used_count", coupon.get("use_count", 0))
        total_count = coupon.get("total_count", coupon.get("count", 0))
        usage_rate = round(used_count / max(total_count, 1), 4) if total_count else 0

        return {
            "coupon_id": coupon.get("id", coupon_id),
            "coupon_name": coupon.get("name", ""),
            "type": coupon.get("type"),
            "amount": coupon.get("amount", coupon.get("discount", 0)),
            "min_point": coupon.get("min_point", coupon.get("min_amount", 0)),
            "total_issued": total_count,
            "used_count": used_count,
            "usage_rate": usage_rate,
            "status": coupon.get("status"),
            "start_time": coupon.get("start_time", ""),
            "end_time": coupon.get("end_time", ""),
            "history_total": total_history,
            "recent_histories": [
                {
                    "member_id": h.get("member_id", h.get("user_id", "")),
                    "member_name": h.get("member_name", h.get("username", "")),
                    "used_time": h.get("used_time", h.get("create_time", "")),
                    "order_sn": h.get("order_sn", ""),
                    "use_status": h.get("use_status", ""),
                }
                for h in histories[:20]
            ],
        }

    async def _analyze_all(
        self, client: httpx.AsyncClient, hdrs: dict[str, str]
    ) -> dict:
        # Fetch all coupons (first 2 pages to capture most)
        all_coupons: list[dict[str, Any]] = []
        for page in (1, 2):
            resp = await client.get(
                f"{MARKETPLACE_URL}/api/v1/admin/coupons",
                params={"page": page, "page_size": 50},
                headers=hdrs,
            )
            resp.raise_for_status()
            data = resp.json()
            inner = data.get("data", data)
            coupons = inner.get("items", [])
            if not coupons:
                break
            all_coupons.extend(coupons)
            if page * 50 >= inner.get("total", 0):
                break

        total_used = 0
        total_issued = 0
        active_count = 0
        expired_count = 0
        coupon_stats: list[dict[str, Any]] = []

        # Coupon type mapping
        type_map: dict[int, str] = {
            0: "full_reduction",
            1: "fixed_amount",
            2: "discount",
        }

        for c in all_coupons:
            used = c.get("used_count", c.get("use_count", 0))
            issued = c.get("total_count", c.get("count", 0))
            total_used += used
            total_issued += issued

            status = c.get("status", 0)
            if status == 1:
                active_count += 1
            else:
                expired_count += 1

            coupon_stats.append(
                {
                    "coupon_id": c.get("id", ""),
                    "coupon_name": c.get("name", ""),
                    "type": type_map.get(c.get("type", 0), f"type_{c.get('type')}"),
                    "used": used,
                    "issued": issued,
                    "usage_rate": round(used / max(issued, 1), 4) if issued else 0,
                    "status": status,
                }
            )

        # Sort by usage rate descending
        coupon_stats.sort(key=lambda x: x["usage_rate"], reverse=True)

        # Find top 3 and bottom 3
        top_performers = coupon_stats[:3]
        low_performers = [c for c in coupon_stats if c["issued"] > 0]
        low_performers.sort(key=lambda x: x["usage_rate"])
        bottom_performers = low_performers[:3]

        return {
            "total_coupons": len(all_coupons),
            "active_coupons": active_count,
            "expired_coupons": expired_count,
            "total_used": total_used,
            "total_issued": total_issued,
            "overall_usage_rate": (
                round(total_used / max(total_issued, 1), 4) if total_issued else 0
            ),
            "top_performers": top_performers,
            "low_performers": bottom_performers,
            "all_coupons": coupon_stats,
        }

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
