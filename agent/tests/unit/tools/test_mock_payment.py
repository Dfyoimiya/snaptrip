"""Tests for MockPaymentTool — payment processing tool."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.tools.implementations.mock_payment import MockPaymentTool
from agent.tools.implementations.base import ToolResult


class TestMockPaymentTool:
    """Tests for MockPaymentTool."""

    def test_tool_metadata(self):
        """Tool has correct name, description, and metadata."""
        tool = MockPaymentTool()
        assert tool.name == "mock_payment_charge"
        assert tool.is_read_only is False
        assert tool.cost_model == "mock"
        assert tool.tool_timeout == 15.0
        assert tool.args_schema is not None

    @pytest.mark.asyncio
    async def test_payment_success(self, freeze_random):
        """A successful payment charge."""
        tool = MockPaymentTool()
        result = await tool._arun(
            order_id="ord-001",
            amount_cny=68.0,
            idempotency_key="idem-pay-001",
        )
        assert result.success is True
        assert result.data["payment_id"].startswith("pay-")
        assert result.data["status"] == "charged"
        assert result.data["amount_cny"] == 68.0
        assert result.cost_cny == 68.0
        assert result.idempotency_key == "idem-pay-001"

    @pytest.mark.asyncio
    async def test_idempotency_no_double_charge(self, freeze_random):
        """Using the same idempotency key returns the existing payment."""
        tool = MockPaymentTool()
        # First charge
        r1 = await tool._arun(order_id="ord-001", amount_cny=68.0, idempotency_key="idem-key")
        assert r1.data["status"] == "charged"

        # Second charge with same key
        r2 = await tool._arun(order_id="ord-001", amount_cny=68.0, idempotency_key="idem-key")
        assert r2.data["status"] == "already_charged"
        assert r2.data["payment_id"] == r1.data["payment_id"]

    @pytest.mark.asyncio
    async def test_random_failure(self, force_random_failure):
        """~5% random failure produces error ToolResult."""
        tool = MockPaymentTool()
        result = await tool._arun(order_id="ord-001", amount_cny=50.0)
        assert result.success is False
        assert "timeout" in result.data["error"]

    @pytest.mark.asyncio
    async def test_payment_without_idempotency_key(self, freeze_random):
        """Payment works without an explicit idempotency key."""
        tool = MockPaymentTool()
        result = await tool._arun(order_id="ord-002", amount_cny=120.0)
        assert result.success is True
        assert result.data["status"] == "charged"
        assert result.idempotency_key != ""  # Auto-generated

    @pytest.mark.asyncio
    async def test_compensation_creates_refund_action(self):
        """Compensation creates a refund action."""
        tool = MockPaymentTool()
        result = ToolResult(
            success=True,
            data={"order_id": "ord-001", "amount_cny": 68.0},
            idempotency_key="idem-pay-001",
        )
        action = tool.compensation({}, result)
        assert "refund:" in action.action_id
        assert "idem-pay-001" in action.action_id
        assert action.max_retries == 3

    @pytest.mark.asyncio
    async def test_compensation_execute_refunds_payment(self, freeze_random):
        """Executing the compensation refunds the payment."""
        tool = MockPaymentTool()
        # First charge
        charge_result = await tool._arun(
            order_id="ord-001", amount_cny=68.0, idempotency_key="refund-test",
        )
        assert charge_result.data["status"] == "charged"

        # Now refund
        action = tool.compensation({}, charge_result)
        await action.execute()

        from agent.tools.implementations.mock_payment import _MOCK_PAYMENTS
        assert _MOCK_PAYMENTS["refund-test"]["status"] == "refunded"
        assert _MOCK_PAYMENTS["refund-test"]["refunded"] is True

    @pytest.mark.asyncio
    async def test_refund_nonexistent_payment(self):
        """Refunding a non-existent payment does not raise."""
        tool = MockPaymentTool()
        result = ToolResult(
            success=True,
            data={"order_id": "nonexistent"},
            idempotency_key="nonexistent-key",
        )
        action = tool.compensation({}, result)
        await action.execute()  # Should not raise
