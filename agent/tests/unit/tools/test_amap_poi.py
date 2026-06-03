"""Tests for AmapPOITool — POI search tool.

No seed data. All results come from the Amap adapter (mocked in tests).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.implementations.amap_poi import AmapPOITool
from agent.tools.implementations.base import ToolResult


_MOCK_POIS: list[dict] = [
    {"id": "poi-1", "name": "亲子乐园", "type": "attraction", "lat": 39.93, "lng": 116.45,
     "tags": ["亲子", "室外"], "rating": 4.8, "avg_price": 150, "child_friendly": True},
    {"id": "poi-2", "name": "博物馆", "type": "museum", "lat": 39.92, "lng": 116.40,
     "tags": ["文化", "室内"], "rating": 4.6, "avg_price": 60, "child_friendly": True},
    {"id": "poi-3", "name": "密室逃脱", "type": "escape_room", "lat": 39.94, "lng": 116.42,
     "tags": ["热闹"], "rating": 4.3, "avg_price": 200, "child_friendly": False},
    {"id": "poi-4", "name": "日料餐厅", "type": "japanese", "lat": 39.91, "lng": 116.44,
     "tags": ["日料"], "rating": 4.9, "avg_price": 300, "child_friendly": False},
]


def _mock_adapter(pois: list[dict] | None = None) -> MagicMock:
    adapter = MagicMock()
    adapter.search_pois_around = AsyncMock(
        return_value=list(_MOCK_POIS) if pois is None else pois
    )
    return adapter


class TestAmapPOITool:
    """Tests for AmapPOITool."""

    def test_tool_metadata(self):
        """Tool has correct name, description, and metadata."""
        tool = AmapPOITool()
        assert tool.name == "amap_poi_search"
        assert tool.is_read_only is True
        assert tool.cost_model == "free"
        assert tool.tool_timeout == 5.0
        assert tool.args_schema is not None

    @pytest.mark.asyncio
    async def test_no_seed_fallback_returns_error(self):
        """When adapter fails, tool returns error — no seed data fallback."""
        tool = AmapPOITool()

        adapter = MagicMock()
        adapter.search_pois_around = AsyncMock(side_effect=Exception("API down"))

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=adapter):
            result = await tool._arun(lat=39.9, lng=116.4)
            assert result.success is False
            assert "error" in result.data
            assert result.data["pois"] == []
            assert result.data["count"] == 0

    @pytest.mark.asyncio
    async def test_child_friendly_filter(self):
        """child_friendly=True filters out non-child-friendly results."""
        tool = AmapPOITool()
        adapter = _mock_adapter()

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=adapter):
            result = await tool._arun(lat=39.9, lng=116.4, child_friendly=True)
            for poi in result.data["pois"]:
                assert poi.get("child_friendly") is True

    @pytest.mark.asyncio
    async def test_budget_filter(self):
        """Results exceeding budget_per_person are excluded."""
        tool = AmapPOITool()
        adapter = _mock_adapter()

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=adapter):
            result = await tool._arun(lat=39.9, lng=116.4, budget_per_person=1)
            for poi in result.data["pois"]:
                assert poi.get("avg_price", 0) <= 1

    @pytest.mark.asyncio
    async def test_max_results_limit(self):
        """Results respect max_results limit."""
        tool = AmapPOITool()
        adapter = _mock_adapter()

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=adapter):
            result = await tool._arun(lat=39.9, lng=116.4, max_results=2)
            assert len(result.data["pois"]) <= 2

    @pytest.mark.asyncio
    async def test_sorted_by_rating(self):
        """Results are sorted by rating descending."""
        tool = AmapPOITool()
        adapter = _mock_adapter()

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=adapter):
            result = await tool._arun(lat=39.9, lng=116.4)
            ratings = [p.get("rating", 0) for p in result.data["pois"]]
            assert ratings == sorted(ratings, reverse=True)

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self):
        """When Amap returns no POIs, returns empty list — no fabrication."""
        tool = AmapPOITool()
        adapter = _mock_adapter([])

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=adapter):
            result = await tool._arun(lat=39.9, lng=116.4)
            assert result.success is True
            assert result.data["pois"] == []
            assert result.data["count"] == 0

    @pytest.mark.asyncio
    async def test_compensation_is_noop(self):
        """Compensation returns a no-op action."""
        tool = AmapPOITool()
        result = ToolResult(success=True, data={}, idempotency_key="ik")
        action = tool.compensation({}, result)
        assert "cache_invalidate" in action.action_id

    @pytest.mark.asyncio
    async def test_amap_integration_success(self):
        """When adapter is available, AMAP results are used."""
        tool = AmapPOITool()

        adapter = _mock_adapter([
            {
                "id": "poi-ext-1", "name": "外部餐厅", "type": "restaurant",
                "lat": 39.93, "lng": 116.45, "rating": 4.8, "avg_price": 80,
                "tags": ["中式"], "child_friendly": True, "distance_km": 0.5,
            },
        ])

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=adapter):
            result = await tool._arun(lat=39.9, lng=116.4)
            assert result.success is True
            assert len(result.data["pois"]) == 1
            assert result.data["pois"][0]["name"] == "外部餐厅"

    @pytest.mark.asyncio
    async def test_amap_integration_failure_returns_error(self):
        """When adapter raises, returns error — no seed data fallback."""
        tool = AmapPOITool()

        adapter = MagicMock()
        adapter.search_pois_around = AsyncMock(side_effect=Exception("API down"))

        with patch("agent.adapters.amap_adapter.get_adapter", return_value=adapter):
            result = await tool._arun(lat=39.9, lng=116.4)
            assert result.success is False
            assert result.data["count"] == 0
