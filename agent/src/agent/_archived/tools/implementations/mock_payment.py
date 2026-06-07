# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 ARCHIVED — TRIP PLANNING AGENT                      ║
# ║  Archived: 2026-06-07                                                        ║
# ║  Reason: Agent repurposed from local trip planning to new domain             ║
# ║  This file is preserved for reference but NOT imported by the framework.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

"""MockPaymentTool — payment processing with idempotency protection.

Mutable tool: charges payment; compensation = refund.
Uses idempotency_key to prevent double-charge on retry.
"""

from __future__ import annotations

import random
import uuid
from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

_MOCK_PAYMENTS: dict[str, dict[str, Any]] = {}
_CHARGED_KEYS: set[str] = set()


class PaymentInput(BaseModel):
    """Input schema for mock payment."""

    order_id: str = Field(description="Order ID to charge")
    amount_cny: float = Field(description="Amount to charge in CNY")
    idempotency_key: str = Field(default="", description="Idempotency key to prevent double-charge")


class MockPaymentTool(SmartDayBaseTool):
    """Process payments with idempotency protection.

    Contract:
      - mutable: creates payment records
      - compensation: refund (idempotent)
      - failure rate: ~5%
      - timeout: 15 s
    """

    name: str = "mock_payment_charge"
    description: str = (
        "Charge a payment for an order. Each charge is protected by an idempotency key "
        "— calling with the same key twice returns the original payment without "
        "double-charging. Use this tool during the execution phase after all orders "
        "have been confirmed."
    )
    args_schema: type[BaseModel] = PaymentInput
    is_read_only: bool = False
    cost_model: str = "mock"
    tool_timeout: float = 15.0

    async def _arun(
        self,
        order_id: str = "",
        amount_cny: float = 0.0,
        idempotency_key: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        # Idempotency check
        if idempotency_key and idempotency_key in _CHARGED_KEYS:
            existing = _MOCK_PAYMENTS.get(idempotency_key, {})
            return ToolResult(
                success=True,
                data={
                    "payment_id": existing.get("payment_id", ""),
                    "order_id": order_id, "amount_cny": amount_cny,
                    "status": "already_charged",
                },
                cost_cny=amount_cny,
                idempotency_key=idempotency_key,
            )

        # ~5% simulated failure
        if random.random() < 0.05:
            return ToolResult(success=False, data={"error": "Mock payment gateway timeout"})

        payment_id = f"pay-{uuid.uuid4().hex[:8].upper()}"
        _MOCK_PAYMENTS[idempotency_key or payment_id] = {
            "payment_id": payment_id, "order_id": order_id,
            "amount_cny": amount_cny, "status": "charged", "refunded": False,
        }
        if idempotency_key:
            _CHARGED_KEYS.add(idempotency_key)

        return ToolResult(
            success=True,
            data={
                "payment_id": payment_id, "order_id": order_id,
                "amount_cny": amount_cny, "status": "charged",
            },
            cost_cny=amount_cny,
            idempotency_key=idempotency_key or payment_id,
        )

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        idem_key = result.idempotency_key
        order_id = result.data.get("order_id", "")
        amount = result.data.get("amount_cny", 0.0)
        return CompensationAction(
            action_id=f"refund:{idem_key}",
            tool_name=self.name,
            description=f"Refund payment {idem_key} for order {order_id} (¥{amount})",
            execute=self._refund(idem_key),
            max_retries=3,
        )

    @staticmethod
    def _refund(idem_key: str):
        async def _refund_action() -> None:
            if idem_key in _MOCK_PAYMENTS:
                _MOCK_PAYMENTS[idem_key]["status"] = "refunded"
                _MOCK_PAYMENTS[idem_key]["refunded"] = True
        return _refund_action
