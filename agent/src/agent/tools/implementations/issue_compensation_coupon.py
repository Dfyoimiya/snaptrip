"""Issue compensation coupon tool — grant a coupon as service recovery (write, Saga)."""

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


class IssueCompensationCouponArgs(BaseModel):
    order_id: str = Field(..., description="Order ID the compensation is related to")
    amount: float = Field(..., description="Coupon amount in CNY", ge=0, le=99999.99)
    reason: str = Field(..., description="Reason for compensation")
    member_id: str = Field(..., description="Member ID to issue coupon to")


class IssueCompensationCouponTool(SmartDayBaseTool):
    name: str = "issue_compensation_coupon"
    description: str = (
        "Issue a compensation coupon to a customer as service recovery. "
        "Use sparingly — only when the company is clearly at fault "
        "(shipping delays, damaged items, wrong items sent, service failures). "
        "Returns the coupon ID and confirmation message."
    )
    is_read_only: bool = False
    cost_model: str = "free"
    args_schema: type[BaseModel] = IssueCompensationCouponArgs
    tool_timeout: float = 10.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            payload: dict[str, Any] = {
                "order_id": kwargs["order_id"],
                "amount": kwargs["amount"],
                "reason": kwargs["reason"],
                "member_id": kwargs["member_id"],
            }
            hdrs = auth_header()
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.post(
                    f"{MARKETPLACE_URL}/api/v1/portal/cs/compensate",
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
        """Coupon issuance is irreversible — admin must manually revoke the coupon."""
        amount = args.get("amount", 0)
        order_id = args.get("order_id", "unknown")

        async def _coupon_rollback() -> None:
            logger.warning(
                "IssueCompensationCoupon compensation: ¥%s coupon for order %s "
                "is irreversible. Admin must manually revoke the coupon.",
                amount,
                order_id,
            )

        return CompensationAction(
            action_id=self._idem_key(args),
            tool_name=self.name,
            description=f"Compensation-coupon rollback (¥{amount}) for order {order_id} (no-op: requires manual admin action)",
            execute=_coupon_rollback,
        )
