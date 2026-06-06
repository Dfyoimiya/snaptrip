"""Tests for PymooSolverTool -- NSGA-II multi-objective itinerary optimizer.

Pymoo's actual NSGA-II is mocked (via `pymoo.optimize.minimize`) to
keep tests fast and deterministic while exercising the full tool wrapper
logic (input extraction, result parsing, feasible/infeasible sorting,
bounds checking, exception handling).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

pymoo = pytest.importorskip("pymoo")  # skip entire module if pymoo not available

from agent.tools.implementations.base import ToolResult
from agent.tools.implementations.pymoo_solver import (
    PymooSolverInput,
    PymooSolverTool,
)
from agent.tools.transaction.compensation import CompensationAction

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------
_ACTIVITIES = [
    {"id": "act-1", "name": "公园", "lat": 39.92, "lng": 116.40, "avg_price": 0, "rating": 4.5, "child_friendly": True},
    {"id": "act-2", "name": "密室", "lat": 39.93, "lng": 116.42, "avg_price": 128, "rating": 4.3, "child_friendly": False},
    {"id": "act-3", "name": "博物馆", "lat": 39.91, "lng": 116.39, "avg_price": 60, "rating": 4.7, "child_friendly": True},
]
_RESTAURANTS = [
    {"id": "rst-1", "name": "亲子餐厅", "lat": 39.92, "lng": 116.41, "avg_price": 80, "rating": 4.6, "child_friendly": True, "dietary_tags": ["vegetarian"]},
    {"id": "rst-2", "name": "牛排馆", "lat": 39.94, "lng": 116.43, "avg_price": 300, "rating": 4.8, "child_friendly": False, "dietary_tags": []},
]


def _make_mock_minimize_result() -> MagicMock:
    """Create a mock pymoo minimize result returning 3 Pareto solutions.

    Solutions (act_idx, rst_idx) -> (activity, restaurant):
      0 -> act-1 (park, free)   + rst-1 (family restaurant, 80)   = 160  (feasible)
      1 -> act-2 (escape room)  + rst-2 (steakhouse, 300)         = 856  (over budget)
      2 -> act-3 (museum, 60)   + rst-1 (family restaurant, 80)   = 120  (feasible)
    """
    mock_res = MagicMock()
    mock_res.X = np.array([[0, 0], [1, 1], [2, 0]], dtype=int)
    # Objectives: (rating, cost, transit, preference) -- all minimized
    mock_res.F = np.array([
        [-4.55, 160.0, 30.0, -0.5],    # high rating, low cost, good transit
        [-4.55, 856.0, 45.0, -0.5],    # high rating, over-budget, ok transit
        [-4.65, 120.0, 25.0, -0.5],    # best rating, lowest cost, best transit
    ])
    # Constraints: (budget_violation, time_violation)
    mock_res.G = np.array([
        [0.0, 0.0],     # feasible
        [356.0, 0.0],   # budget exceeded by 356
        [0.0, 0.0],     # feasible
    ])
    return mock_res


def _make_mock_minimize_result_out_of_bounds() -> MagicMock:
    """Create a mock with one out-of-bounds index to test the bounds guard.

    Solution 1 requests act_idx=0 (valid) and rst_idx=5 (invalid).
    Solution 2 requests act_idx=10 (invalid) and rst_idx=0 (valid).
    Solution 3 is valid.
    """
    mock_res = MagicMock()
    mock_res.X = np.array([[0, 5], [10, 0], [2, 1]], dtype=int)
    mock_res.F = np.array([
        [-4.55, 160.0, 30.0, -0.5],
        [-4.65, 120.0, 25.0, -0.5],
        [-4.70, 360.0, 35.0, -0.5],
    ])
    mock_res.G = np.array([
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
    ])
    return mock_res


# ===========================================================================
# Tests
# ===========================================================================


class TestPymooSolverTool:
    """Tests for PymooSolverTool."""

    # -- Metadata -----------------------------------------------------------

    def test_tool_metadata(self):
        """Tool exposes correct name, is_read_only, cost_model, timeout, and args_schema."""
        tool = PymooSolverTool()
        assert tool.name == "pymoo_solve_itinerary"
        assert tool.is_read_only is True
        assert tool.cost_model == "free"
        assert tool.tool_timeout == 30.0
        assert tool.args_schema is not None
        assert tool.args_schema == PymooSolverInput

    # -- Positive cases -----------------------------------------------------

    @pytest.mark.asyncio
    async def test_solve_basic(self):
        """Valid activities + restaurants returns Pareto solutions with success=True."""
        tool = PymooSolverTool()
        mock_res = _make_mock_minimize_result()

        with patch("agent.tools.implementations.pymoo_solver.minimize") as mock_minimize:
            mock_minimize.return_value = mock_res
            result = await tool._arun(
                activities=_ACTIVITIES.copy(),
                restaurants=_RESTAURANTS.copy(),
                budget=500,
            )

        assert result.success is True
        assert result.data["solver"] == "pymoo_nsga2"
        assert result.data["total_generated"] == 3
        assert result.data["feasible_count"] == 2  # solutions 0 and 2
        assert len(result.data["pareto_solutions"]) > 0  # feasible first

        # Verify structure of a single solution
        first = result.data["pareto_solutions"][0]
        assert first["feasible"] is True
        assert first["rank"] >= 1
        assert "activity" in first
        assert first["activity"]["id"] == "act-1"
        assert "restaurant" in first
        assert "objectives" in first
        assert "rating_score" in first["objectives"]
        assert "total_cost" in first["objectives"]
        assert "transit_time_min" in first["objectives"]
        assert "preference_match" in first["objectives"]

    @pytest.mark.asyncio
    async def test_solve_with_custom_budget_and_constraints(self):
        """Custom budget, guest_count, child_friendly, and dietary restrictions are passed through."""
        tool = PymooSolverTool()
        mock_res = _make_mock_minimize_result()

        with patch("agent.tools.implementations.pymoo_solver.minimize") as mock_minimize:
            mock_minimize.return_value = mock_res
            result = await tool._arun(
                activities=_ACTIVITIES.copy(),
                restaurants=_RESTAURANTS.copy(),
                budget=1000,
                guest_count=3,
                child_friendly_required=True,
                dietary_restrictions=["vegetarian"],
                origin_lat=39.92,
                origin_lng=116.40,
            )

        assert result.success is True
        assert result.data["feasible_count"] == 2

    @pytest.mark.asyncio
    async def test_single_option(self):
        """Trivial case with one activity and one restaurant still succeeds."""
        tool = PymooSolverTool()
        mock_res = _make_mock_minimize_result()

        with patch("agent.tools.implementations.pymoo_solver.minimize") as mock_minimize:
            mock_minimize.return_value = mock_res
            result = await tool._arun(
                activities=[_ACTIVITIES[0].copy()],
                restaurants=[_RESTAURANTS[0].copy()],
                budget=500,
            )

        assert result.success is True
        assert "pareto_solutions" in result.data

    @pytest.mark.asyncio
    async def test_out_of_bounds_indices_skipped(self):
        """Pareto solutions with out-of-bounds activity/restaurant indices are skipped."""
        tool = PymooSolverTool()
        mock_res = _make_mock_minimize_result_out_of_bounds()

        with patch("agent.tools.implementations.pymoo_solver.minimize") as mock_minimize:
            mock_minimize.return_value = mock_res
            result = await tool._arun(
                activities=_ACTIVITIES.copy(),      # 3 activities (indices 0-2)
                restaurants=_RESTAURANTS.copy(),     # 2 restaurants (indices 0-1)
                budget=500,
            )

        # Only 1 valid solution out of 3 (solution 3: act_idx=2, rst_idx=1)
        assert result.success is True
        assert result.data["total_generated"] == 1
        assert len(result.data["pareto_solutions"]) == 1
        assert result.data["pareto_solutions"][0]["activity"]["id"] == "act-3"

    # -- Negative cases -----------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_candidates(self):
        """Empty activities or restaurants returns an error ToolResult."""
        tool = PymooSolverTool()

        result = await tool._arun(activities=[], restaurants=_RESTAURANTS.copy())
        assert result.success is False
        assert "error" in result.data

        result = await tool._arun(activities=_ACTIVITIES.copy(), restaurants=[])
        assert result.success is False
        assert "error" in result.data

        result = await tool._arun(activities=[], restaurants=[])
        assert result.success is False
        assert "error" in result.data

    @pytest.mark.asyncio
    async def test_minimize_exception(self):
        """When pymoo minimize raises an exception, an error ToolResult is returned."""
        tool = PymooSolverTool()

        with patch("agent.tools.implementations.pymoo_solver.minimize") as mock_minimize:
            mock_minimize.side_effect = RuntimeError("pymoo solver crashed")
            result = await tool._arun(
                activities=_ACTIVITIES.copy(),
                restaurants=_RESTAURANTS.copy(),
                budget=500,
            )

        assert result.success is False
        assert "error" in result.data
        assert "pymoo optimization failed" in result.data["error"]
        assert "pymoo solver crashed" in result.data["error"]

    @pytest.mark.asyncio
    async def test_activities_none(self):
        """None activities returns an error (treated as falsy)."""
        tool = PymooSolverTool()
        result = await tool._arun(activities=None, restaurants=_RESTAURANTS.copy())
        assert result.success is False
        assert "error" in result.data

    @pytest.mark.asyncio
    async def test_restaurants_none(self):
        """None restaurants returns an error."""
        tool = PymooSolverTool()
        result = await tool._arun(activities=_ACTIVITIES.copy(), restaurants=None)
        assert result.success is False
        assert "error" in result.data

    # -- Compensation -------------------------------------------------------

    def test_compensation_is_noop(self):
        """compensation() returns a no-op CompensationAction."""
        tool = PymooSolverTool()
        action = tool.compensation(args={}, result=MagicMock(spec=ToolResult))
        assert isinstance(action, CompensationAction)
        assert action.action_id == "pymoo_noop"
        assert action.tool_name == "pymoo_solve_itinerary"
        assert "no-op" in action.description.lower()

    # -- Schema -------------------------------------------------------------

    def test_args_schema_validates_positive_guest_count(self):
        """PymooSolverInput enforces guest_count >= 1."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PymooSolverInput(guest_count=0)

    def test_args_schema_defaults(self):
        """PymooSolverInput provides sensible defaults."""
        schema = PymooSolverInput()
        assert schema.budget == 500
        assert schema.guest_count == 2
        assert schema.child_friendly_required is False
        assert schema.dietary_restrictions == []
        assert schema.activity_location is None
