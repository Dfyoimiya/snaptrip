"""Tests for AmapGeocodeTool — geocoding tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.implementations.amap_geocode import AmapGeocodeTool
from agent.tools.implementations.base import ToolResult


class TestAmapGeocodeTool:
    """Tests for AmapGeocodeTool."""

    def test_tool_metadata(self):
        """Tool has correct name, description, and metadata."""
        tool = AmapGeocodeTool()
        assert tool.name == "amap_geocode"
        assert tool.is_read_only is True
        assert tool.cost_model == "free"
        assert tool.tool_timeout == 5.0
        assert tool.args_schema is not None

    @pytest.mark.asyncio
    async def test_geocode_address(self):
        """Geocode an address via adapter."""
        tool = AmapGeocodeTool()

        mock_adapter = MagicMock()
        mock_adapter.geocode = AsyncMock(return_value={
            "lat": 39.9219, "lng": 116.4435,
            "city": "北京市", "address": "北京市东城区",
        })

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=mock_adapter):
            result = await tool._arun(address="东城区", city="北京")
            assert result.success is True
            assert result.data["lat"] == 39.9219
            assert result.data["lng"] == 116.4435

    @pytest.mark.asyncio
    async def test_reverse_geocode(self):
        """Reverse geocode a location via adapter."""
        tool = AmapGeocodeTool()

        mock_adapter = MagicMock()
        mock_adapter.reverse_geocode = AsyncMock(return_value={
            "lat": 39.9219, "lng": 116.4435,
            "address": "北京市东城区某地",
        })

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=mock_adapter):
            result = await tool._arun(location="116.4435,39.9219")
            assert result.success is True
            assert "北京市" in result.data["address"]

    @pytest.mark.asyncio
    async def test_ip_location(self):
        """Locate by IP via adapter."""
        tool = AmapGeocodeTool()

        mock_adapter = MagicMock()
        mock_adapter.ip_location = AsyncMock(return_value={
            "city": "上海", "province": "上海市", "adcode": "310000",
        })
        mock_adapter.geocode = AsyncMock(return_value={
            "lat": 31.2304, "lng": 121.4737,
            "city": "上海", "address": "上海市",
        })

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=mock_adapter):
            result = await tool._arun(ip="1.2.3.4")
            assert result.success is True
            assert result.data["city"] == "上海"
            assert result.data["lat"] == 31.2304

    @pytest.mark.asyncio
    async def test_ip_location_geocode_failure_falls_back(self):
        """When geocode fails after ip_location, falls into except block returning Beijing default."""
        tool = AmapGeocodeTool()

        mock_adapter = MagicMock()
        mock_adapter.ip_location = AsyncMock(return_value={"city": "深圳"})
        mock_adapter.geocode = AsyncMock(side_effect=Exception("down"))

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=mock_adapter):
            result = await tool._arun(ip="1.2.3.4")
            assert result.success is True
            # The entire ip_location+geocode block is wrapped in one try/except,
            # so geocode failure falls into the except and returns hardcoded 北京
            assert result.data["city"] == "北京"

    @pytest.mark.asyncio
    async def test_ip_location_total_failure_falls_back(self):
        """When everything fails for IP, returns Beijing default."""
        tool = AmapGeocodeTool()

        mock_adapter = MagicMock()
        mock_adapter.ip_location = AsyncMock(side_effect=Exception("down"))

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=mock_adapter):
            result = await tool._arun(ip="1.2.3.4")
            assert result.success is True
            assert result.data["city"] == "北京"

    @pytest.mark.asyncio
    async def test_no_args_returns_ip_location(self):
        """When no address/location/ip given, tries IP location."""
        tool = AmapGeocodeTool()

        mock_adapter = MagicMock()
        mock_adapter.ip_location = AsyncMock(return_value={"city": "北京"})
        mock_adapter.geocode = AsyncMock(return_value={
            "lat": 39.9219, "lng": 116.4435, "city": "北京", "address": "",
        })

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=mock_adapter):
            result = await tool._arun()
            assert result.success is True

    @pytest.mark.asyncio
    async def test_compensation_is_noop(self):
        """Compensation returns a no-op action."""
        tool = AmapGeocodeTool()
        result = ToolResult(success=True, data={}, idempotency_key="gk")
        action = tool.compensation({}, result)
        assert "geo_cache" in action.action_id
