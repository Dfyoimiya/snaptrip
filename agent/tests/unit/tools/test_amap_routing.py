"""Tests for AmapRoutingTool — travel time estimation tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.implementations.amap_routing import AmapRoutingTool
from agent.tools.implementations.base import ToolResult


class TestAmapRoutingTool:
    """Tests for AmapRoutingTool."""

    def test_tool_metadata(self):
        """Tool has correct name, description, and metadata."""
        tool = AmapRoutingTool()
        assert tool.name == "amap_routing"
        assert tool.is_read_only is True
        assert tool.cost_model == "free"
        assert tool.tool_timeout == 8.0
        assert tool.args_schema is not None

    @pytest.mark.asyncio
    async def test_euclidean_fallback(self):
        """When adapter is unavailable, returns Euclidean fallback."""
        tool = AmapRoutingTool()
        result = await tool._arun(from_lat=39.9, from_lng=116.4, to_lat=39.95, to_lng=116.45)
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "distance_km" in result.data
        assert "duration_min" in result.data
        assert result.data["distance_km"] > 0
        assert result.data["duration_min"] >= 5
        assert result.idempotency_key != ""

    @pytest.mark.asyncio
    async def test_different_modes(self):
        """Different travel modes yield different durations."""
        tool = AmapRoutingTool()
        driving = await tool._arun(from_lat=39.9, from_lng=116.4, to_lat=39.95, to_lng=116.45, mode="driving")
        walking = await tool._arun(from_lat=39.9, from_lng=116.4, to_lat=39.95, to_lng=116.45, mode="walking")
        # Walking should take longer than driving
        assert walking.data["duration_min"] > driving.data["duration_min"]

    @pytest.mark.asyncio
    async def test_compensation_is_noop(self):
        """Compensation returns a no-op action."""
        tool = AmapRoutingTool()
        result = ToolResult(success=True, data={}, idempotency_key="rk")
        action = tool.compensation({}, result)
        assert "route_cache" in action.action_id

    @pytest.mark.asyncio
    async def test_amap_integration_success(self):
        """When adapter is available, AMAP results are used."""
        tool = AmapRoutingTool()

        mock_adapter = MagicMock()
        mock_adapter.estimate_travel_time = AsyncMock(return_value={
            "distance_km": 12.5,
            "duration_min": 25.0,
        })

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=mock_adapter):
            result = await tool._arun(from_lat=39.9, from_lng=116.4, to_lat=39.95, to_lng=116.45)
            assert result.success is True
            assert result.data["distance_km"] == 12.5
            assert result.data["duration_min"] == 25.0

    @pytest.mark.asyncio
    async def test_amap_integration_failure_falls_back(self):
        """When adapter raises, falls back to Euclidean calculation."""
        tool = AmapRoutingTool()

        mock_adapter = MagicMock()
        mock_adapter.estimate_travel_time = AsyncMock(side_effect=Exception("API down"))

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=mock_adapter):
            result = await tool._arun(from_lat=39.9, from_lng=116.4, to_lat=39.95, to_lng=116.45)
            assert result.success is True
            assert result.data["distance_km"] > 0
            assert result.data["duration_min"] >= 5

    @pytest.mark.asyncio
    async def test_same_point_zero_distance(self):
        """Routing from a point to itself yields ~0 distance."""
        tool = AmapRoutingTool()
        result = await tool._arun(from_lat=39.9, from_lng=116.4, to_lat=39.9, to_lng=116.4)
        assert result.data["distance_km"] < 1.0

    @pytest.mark.asyncio
    async def test_default_mode_is_driving(self):
        """Default travel mode is driving."""
        tool = AmapRoutingTool()
        result = await tool._arun(from_lat=39.9, from_lng=116.4, to_lat=39.95, to_lng=116.45)
        assert result.data["mode"] == "driving"
