"""Tests for ORToolsCPSATTool -- OR-Tools CP-SAT constraint solver/verifier.

OR-Tools is imported lazily inside `_arun`, so we mock it via `sys.modules`
to avoid requiring the full ortools library at test time.

Python 3.13 removes several magic methods from MagicMock (including __le__),
so we use a lightweight class with explicit comparison support for constraint
expressions returned by ``model.NewBoolVar()``.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from agent.tools.implementations.base import ToolResult
from agent.tools.implementations.or_cpsat import CPSATSolverInput, ORToolsCPSATTool
from agent.tools.transaction.compensation import CompensationAction

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------
_ACTIVITIES = [
    {"id": "act-1", "name": "公园", "avg_price": 0, "rating": 4.5, "child_friendly": True},
    {"id": "act-2", "name": "密室", "avg_price": 128, "rating": 4.3, "child_friendly": False},
    {"id": "act-3", "name": "博物馆", "avg_price": 60, "rating": 4.7, "child_friendly": True},
]
_RESTAURANTS = [
    {"id": "rst-1", "name": "亲子餐厅", "avg_price": 80, "rating": 4.6, "child_friendly": True, "dietary_tags": ["vegetarian"]},
    {"id": "rst-2", "name": "牛排馆", "avg_price": 300, "rating": 4.8, "child_friendly": False, "dietary_tags": []},
]

# ---------------------------------------------------------------------------
# Comparison-supporting variable mock
# ---------------------------------------------------------------------------


class _CmpVar:
    """A mock CP-SAT variable that supports arithmetic and comparison.

    Python 3.13's MagicMock does not implement __le__ or __ge__ natively,
    so we use this class to stand in for ortools ``IntVar`` / ``BoolVar``
    instances in tests.
    """

    def __add__(self, other: object) -> _CmpVar:
        return _CmpVar()

    def __radd__(self, other: object) -> _CmpVar:
        return _CmpVar()

    def __mul__(self, other: object) -> _CmpVar:
        return _CmpVar()

    def __rmul__(self, other: object) -> _CmpVar:
        return _CmpVar()

    def __le__(self, other: object) -> _CmpVar:
        return _CmpVar()

    def __ge__(self, other: object) -> _CmpVar:
        return _CmpVar()

    def __lt__(self, other: object) -> _CmpVar:
        return _CmpVar()

    def __gt__(self, other: object) -> _CmpVar:
        return _CmpVar()

    def __eq__(self, other: object) -> _CmpVar:  # type: ignore[override]
        return _CmpVar()

    def __ne__(self, other: object) -> _CmpVar:  # type: ignore[override]
        return _CmpVar()


# ---------------------------------------------------------------------------
# Mock ortools.cp_model helpers
# ---------------------------------------------------------------------------


class _MockSolver:
    """A mock CpSolver with controllable Solve/Value."""

    def __init__(self, solve_return: str = "OPTIMAL"):
        self.parameters = MagicMock()
        self._solve_return = solve_return

    def Solve(self, model: object) -> str:
        return self._solve_return

    def Value(self, var: object) -> int:
        return 1


def _make_mock_cp_model(solve_return: str = "OPTIMAL") -> MagicMock:
    """Build a mock ``cp_model`` module."""
    mock = MagicMock()
    mock.OPTIMAL = "OPTIMAL"
    mock.FEASIBLE = "FEASIBLE"
    mock.MODEL_INVALID = "MODEL_INVALID"

    mock_model = MagicMock()
    mock_model.NewBoolVar = MagicMock(return_value=_CmpVar())
    mock_model.Add = MagicMock(return_value=MagicMock())
    mock_model.Minimize = MagicMock()
    mock.CpModel.return_value = mock_model

    mock_solver = _MockSolver(solve_return=solve_return)
    mock.CpSolver.return_value = mock_solver

    return mock


@pytest.fixture
def mock_cp_model_feasible():
    """cp_model where solver returns OPTIMAL."""
    mock = _make_mock_cp_model(solve_return="OPTIMAL")
    parent = MagicMock()
    parent.cp_model = mock

    with patch.dict(sys.modules, {
        "ortools": MagicMock(),
        "ortools.sat": MagicMock(),
        "ortools.sat.python": parent,
        "ortools.sat.python.cp_model": mock,
    }):
        yield mock


@pytest.fixture
def mock_cp_model_feasible_non_optimal():
    """cp_model where solver returns FEASIBLE (not OPTIMAL)."""
    mock = _make_mock_cp_model(solve_return="FEASIBLE")
    parent = MagicMock()
    parent.cp_model = mock

    with patch.dict(sys.modules, {
        "ortools": MagicMock(),
        "ortools.sat": MagicMock(),
        "ortools.sat.python": parent,
        "ortools.sat.python.cp_model": mock,
    }):
        yield mock


@pytest.fixture
def mock_cp_model_infeasible():
    """cp_model where solver returns MODEL_INVALID (not OPTIMAL/FEASIBLE)."""
    mock = _make_mock_cp_model(solve_return="MODEL_INVALID")
    parent = MagicMock()
    parent.cp_model = mock

    with patch.dict(sys.modules, {
        "ortools": MagicMock(),
        "ortools.sat": MagicMock(),
        "ortools.sat.python": parent,
        "ortools.sat.python.cp_model": mock,
    }):
        yield mock


# ===========================================================================
# Tests
# ===========================================================================


class TestORToolsCPSATTool:
    """Tests for ORToolsCPSATTool."""

    # -- Metadata -----------------------------------------------------------

    def test_tool_metadata(self):
        """Tool exposes correct name, is_read_only, cost_model, and args_schema."""
        tool = ORToolsCPSATTool()
        assert tool.name == "ortools_cpsat_solve"
        assert tool.is_read_only is True
        assert tool.cost_model == "free"
        assert tool.args_schema is not None
        assert tool.args_schema == CPSATSolverInput

    # -- Mode: feasibility --------------------------------------------------

    @pytest.mark.asyncio
    async def test_feasibility_mode(self, mock_cp_model_feasible):
        """feasibility mode with feasible candidates returns feasible=True."""
        tool = ORToolsCPSATTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            mode="feasibility",
        )
        assert result.success is True
        assert result.data["feasible"] is True
        assert result.data["solver"] == "ortools_cpsat"
        assert result.data["status"] == "OPTIMAL"

    @pytest.mark.asyncio
    async def test_feasibility_mode_non_optimal(self, mock_cp_model_feasible_non_optimal):
        """feasibility mode with FEASIBLE (not OPTIMAL) status still returns feasible=True."""
        tool = ORToolsCPSATTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            mode="feasibility",
        )
        assert result.success is True
        assert result.data["feasible"] is True
        assert result.data["status"] == "FEASIBLE"

    @pytest.mark.asyncio
    async def test_infeasible_mode(self, mock_cp_model_infeasible):
        """feasibility mode with infeasible candidates returns feasible=False."""
        tool = ORToolsCPSATTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=1,
            mode="feasibility",
        )
        assert result.success is True
        assert result.data["feasible"] is False
        assert result.data["status"] == "INFEASIBLE"

    # -- Mode: optimize -----------------------------------------------------

    @pytest.mark.asyncio
    async def test_optimize_mode(self, mock_cp_model_feasible):
        """optimize mode returns a solution with activity and restaurant."""
        tool = ORToolsCPSATTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            mode="optimize",
        )
        assert result.success is True
        assert result.data["feasible"] is True
        assert "activity" in result.data
        assert "restaurant" in result.data
        assert result.data["activity"]["name"]
        assert result.data["restaurant"]["name"]

    # -- Mode: verify -------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_mode(self, mock_cp_model_feasible):
        """verify mode with a candidate solution checks feasibility."""
        tool = ORToolsCPSATTool()
        candidate = {
            "activity": {"name": "公园"},
            "restaurant": {"name": "亲子餐厅"},
        }
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            mode="verify",
            candidate_solution=candidate,
        )
        assert result.success is True
        assert result.data["feasible"] is True

    @pytest.mark.asyncio
    async def test_verify_mode_no_candidate(self, mock_cp_model_feasible):
        """verify mode without a candidate solution acts like feasibility mode."""
        tool = ORToolsCPSATTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            mode="verify",
            candidate_solution=None,
        )
        assert result.success is True
        assert result.data["feasible"] is True

    # -- Constraint application ---------------------------------------------

    @pytest.mark.asyncio
    async def test_child_friendly_constraint(self, mock_cp_model_feasible):
        """child_friendly_required=True filters out non-child-friendly POIs."""
        tool = ORToolsCPSATTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            child_friendly_required=True,
            mode="feasibility",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dietary_restrictions_constraint(self, mock_cp_model_feasible):
        """dietary_restrictions filter restaurants by dietary_tags."""
        tool = ORToolsCPSATTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            dietary_restrictions=["vegetarian"],
            mode="feasibility",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dietary_restrictions_no_match(self, mock_cp_model_feasible):
        """dietary_restrictions with no matching restaurants still runs (model handles via constraints)."""
        tool = ORToolsCPSATTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            dietary_restrictions=["vegan", "gluten_free"],
            mode="feasibility",
        )
        # No restaurant matches both -- model will be infeasible
        assert result.success is True

    # -- Negative: empty candidates ----------------------------------------

    @pytest.mark.asyncio
    async def test_empty_candidates(self):
        """Empty activities or restaurants returns an error ToolResult."""
        tool = ORToolsCPSATTool()

        result = await tool._arun(activities=[], restaurants=_RESTAURANTS.copy())
        assert result.success is False
        assert "error" in result.data

        result = await tool._arun(activities=_ACTIVITIES.copy(), restaurants=[])
        assert result.success is False
        assert "error" in result.data

        result = await tool._arun(activities=[], restaurants=[])
        assert result.success is False
        assert "error" in result.data

    # -- Edge case: ortools not installed -----------------------------------

    @pytest.mark.asyncio
    async def test_ortools_not_installed(self):
        """When ortools is not importable, returns an error with install instructions."""
        tool = ORToolsCPSATTool()
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "ortools":
                raise ImportError("No module named 'ortools'")
            if name == "ortools.sat":
                raise ImportError("No module named 'ortools.sat'")
            if name == "ortools.sat.python":
                raise ImportError("No module named 'ortools.sat.python'")
            if name == "ortools.sat.python.cp_model":
                raise ImportError("No module named 'ortools.sat.python.cp_model'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            sys.modules.pop("ortools", None)
            sys.modules.pop("ortools.sat", None)
            sys.modules.pop("ortools.sat.python", None)
            sys.modules.pop("ortools.sat.python.cp_model", None)

            result = await tool._arun(
                activities=_ACTIVITIES.copy(),
                restaurants=_RESTAURANTS.copy(),
                budget=500,
            )

        assert result.success is False
        assert "ortools not installed" in result.data["error"]

    # -- Compensation -------------------------------------------------------

    def test_compensation_is_noop(self):
        """compensation() returns a no-op CompensationAction."""
        tool = ORToolsCPSATTool()
        action = tool.compensation(args={}, result=MagicMock(spec=ToolResult))
        assert isinstance(action, CompensationAction)
        assert action.action_id == "cpsat_noop"
        assert action.tool_name == "ortools_cpsat_solve"
        assert "no-op" in action.description.lower()

    # -- Schema -------------------------------------------------------------

    def test_args_schema_defaults(self):
        """CPSATSolverInput provides sensible defaults."""
        schema = CPSATSolverInput()
        assert schema.budget == 500
        assert schema.guest_count == 2
        assert schema.child_friendly_required is False
        assert schema.dietary_restrictions == []
        assert schema.mode == "feasibility"
        assert schema.candidate_solution is None
