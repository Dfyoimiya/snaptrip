"""Tests for MockOrderTool — order creation tool."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.tools.implementations.mock_order import MockOrderTool
from agent.tools.implementations.base import ToolResult


class TestMockOrderTool:
    """Tests for MockOrderTool."""

    def test_tool_metadata(self):
        """Tool has correct name, description, and metadata."""
        tool = MockOrderTool()
        assert tool.name == "mock_order_create"
        assert tool.is_read_only is False
        assert tool.cost_model == "mock"
        assert tool.tool_timeout == 10.0
        assert tool.args_schema is not None

    @pytest.mark.asyncio
    async def test_restaurant_order_success(self, freeze_random):
        """A restaurant order is created successfully."""
        tool = MockOrderTool()
        result = await tool._arun(
            order_type="restaurant", poi_id="rst-001",
            guest_count=4, child_count=2, time="18:00",
        )
        assert result.success is True
        assert result.data["order_id"].startswith("bk-rst")
        assert result.data["guest_count"] == 4
        assert result.data["child_count"] == 2
        assert result.data["status"] == "confirmed"
        assert result.data["cost_cny"] > 0
        assert result.cost_cny > 0

    @pytest.mark.asyncio
    async def test_activity_order_with_reserve_only(self, freeze_random):
        """An activity order with reserve_only=True gets 'reserved' status."""
        tool = MockOrderTool()
        result = await tool._arun(
            order_type="activity", poi_id="act-001",
            guest_count=2, time="10:00", reserve_only=True,
        )
        assert result.success is True
        assert result.data["status"] == "reserved"
        assert result.data["order_id"].startswith("bk-act")

    @pytest.mark.asyncio
    async def test_wechat_order(self, freeze_random):
        """A WeChat notification order does not generate a booking ID."""
        tool = MockOrderTool()
        result = await tool._arun(
            order_type="wechat", user_id="user-1",
            message="生日快乐!", recipient="朋友",
        )
        assert result.success is True
        assert result.data["sent"] is True
        assert result.data["recipient"] == "朋友"

    @pytest.mark.asyncio
    async def test_cake_order(self, freeze_random):
        """A cake delivery order is created."""
        tool = MockOrderTool()
        result = await tool._arun(
            order_type="cake", poi_id="bakery-001",
            guest_count=1, delivery_time="15:00",
        )
        assert result.success is True
        assert result.data["order_id"].startswith("ord-cake")
        assert result.data["cost_cny"] == 199.0

    @pytest.mark.asyncio
    async def test_flowers_order(self, freeze_random):
        """A flower delivery order is created."""
        tool = MockOrderTool()
        result = await tool._arun(
            order_type="flowers", poi_id="florist-001",
            delivery_time="12:00",
        )
        assert result.success is True
        assert result.data["order_id"].startswith("ord-flw")
        assert result.data["cost_cny"] == 128.0

    @pytest.mark.asyncio
    async def test_random_failure(self, force_random_failure):
        """~5% random failure produces error ToolResult."""
        tool = MockOrderTool()
        result = await tool._arun(
            order_type="restaurant", poi_id="rst-001",
            guest_count=2, time="18:00",
        )
        assert result.success is False
        assert "unavailable" in result.data["error"]

    @pytest.mark.asyncio
    async def test_compensation_creates_cancel_action(self):
        """Compensation creates a cancel_order action."""
        tool = MockOrderTool()
        result = ToolResult(
            success=True,
            data={"order_id": "bk-rst-ABCD1234", "status": "confirmed"},
            cost_cny=68.0,
        )
        action = tool.compensation({"order_type": "restaurant"}, result)
        assert "cancel_order" in action.action_id
        assert "ABCD1234" in action.action_id
        assert action.max_retries == 3

    @pytest.mark.asyncio
    async def test_compensation_execute_cancels_order(self, freeze_random):
        """Executing the compensation cancels the mock order."""
        tool = MockOrderTool()
        # First create an order
        create_result = await tool._arun(
            order_type="restaurant", poi_id="rst-001",
            guest_count=2, time="18:00",
        )
        assert create_result.data["status"] == "confirmed"

        # Now compensate
        action = tool.compensation({}, create_result)
        await action.execute()

        from agent.tools.implementations.mock_order import _MOCK_ORDERS
        order_id = create_result.data["order_id"]
        assert _MOCK_ORDERS[order_id]["status"] == "CANCELLED"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(self):
        """Cancelling a non-existent order does not raise."""
        tool = MockOrderTool()
        result = ToolResult(
            success=True,
            data={"order_id": "nonexistent-id"},
        )
        action = tool.compensation({}, result)
        await action.execute()  # Should not raise

    @pytest.mark.asyncio
    async def test_cost_calculation_with_children(self, freeze_random):
        """Cost scales with guest_count + child_count*0.5."""
        tool = MockOrderTool()
        result = await tool._arun(
            order_type="restaurant", poi_id="rst-001",
            guest_count=2, child_count=2, time="18:00",
        )
        # base=68, 2 guests + 2*0.5 children = 3 units => 68 * 3 = 204
        assert result.data["cost_cny"] == 68.0 * 3
