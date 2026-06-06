"""Tests for Z3VerifierTool -- hard-constraint feasibility pre-check.

Z3 is imported lazily inside `_arun`, so we mock it via `sys.modules` to
avoid requiring the actual z3-solver library at test time.  The mock z3
module is configured to return deterministic check() results per test case
(sat / unsat with diagnostic solvers).

Python 3.13 removes several magic methods from MagicMock (including __le__),
so we use a plain object with explicit comparison support for expression mocks.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from agent.tools.implementations.base import ToolResult
from agent.tools.implementations.z3_verifier import Z3VerifierInput, Z3VerifierTool
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

# ---------------------------------------------------------------------------
# Comparison-supporting mock for z3 expression values
# ---------------------------------------------------------------------------


class _CmpExpr:
    """A mock z3 expression that supports comparison operators.

    Python 3.13's MagicMock does not implement __le__/__ge__, so we use
    this lightweight class to stand in for z3 expression objects.
    """

    def __le__(self, other: object) -> _CmpExpr:
        return _CmpExpr()

    def __ge__(self, other: object) -> _CmpExpr:
        return _CmpExpr()

    def __lt__(self, other: object) -> _CmpExpr:
        return _CmpExpr()

    def __gt__(self, other: object) -> _CmpExpr:
        return _CmpExpr()

    def __eq__(self, other: object) -> _CmpExpr:  # type: ignore[override]
        return _CmpExpr()

    def __ne__(self, other: object) -> _CmpExpr:  # type: ignore[override]
        return _CmpExpr()


# ---------------------------------------------------------------------------
# Mock Z3 module helpers
# ---------------------------------------------------------------------------


class _MockSolver:
    """A mock Z3 solver whose check() returns a configurable sequence."""

    def __init__(self, check_results: list[str]):
        self._check_results = list(check_results)
        self._call_count = 0

    def set(self, key: str, value: object) -> None:
        pass

    def add(self, constraint: object) -> None:
        pass

    def check(self) -> str:
        idx = self._call_count
        self._call_count += 1
        if idx < len(self._check_results):
            return self._check_results[idx]
        return self._check_results[-1]


class _SolverFactory:
    """Creates a chain of _MockSolver instances for one test run.

    Usage::

        factory = _SolverFactory()
        factory.add_check_results("unsat", "sat")
        mock_z3.Solver = factory
    """

    def __init__(self):
        self._result_lists: list[list[str]] = []

    def add_check_results(self, *results: str) -> None:
        self._result_lists.append(list(results))

    def __call__(self) -> _MockSolver:
        if not self._result_lists:
            return _MockSolver(["sat"])
        results = self._result_lists.pop(0)
        return _MockSolver(results)


def _make_mock_z3() -> MagicMock:
    """Build a MagicMock that stands in for the `z3` module.

    z3.Bool and friends return _CmpExpr instances so that expressions
    like ``z3.Sum(...) <= budget`` work without TypeError.
    """
    mock_z3 = MagicMock()
    mock_z3.sat = "sat"
    mock_z3.unsat = "unsat"

    # These return comparison-supporting expression objects
    mock_z3.Bool.return_value = _CmpExpr()
    mock_z3.PbEq.return_value = _CmpExpr()
    mock_z3.Sum.return_value = _CmpExpr()
    mock_z3.If.return_value = _CmpExpr()
    mock_z3.Not.return_value = _CmpExpr()
    mock_z3.Or.return_value = _CmpExpr()

    return mock_z3


@pytest.fixture
def mock_z3_feasible():
    """Set up a mock z3 module where the first solver returns sat."""
    mock = _make_mock_z3()
    factory = _SolverFactory()
    factory.add_check_results("sat")
    mock.Solver = factory
    with patch.dict(sys.modules, {"z3": mock}):
        yield mock


@pytest.fixture
def mock_z3_infeasible_budget():
    """Set up mock z3: first solver unsat, budget diagnostic solver sat."""
    mock = _make_mock_z3()
    factory = _SolverFactory()
    factory.add_check_results("unsat", "sat")
    mock.Solver = factory
    with patch.dict(sys.modules, {"z3": mock}):
        yield mock


@pytest.fixture
def mock_z3_infeasible_child():
    """Set up mock z3: orig unsat, budget-diag unsat, child-diag sat."""
    mock = _make_mock_z3()
    factory = _SolverFactory()
    factory.add_check_results("unsat", "unsat", "sat")
    mock.Solver = factory
    with patch.dict(sys.modules, {"z3": mock}):
        yield mock


@pytest.fixture
def mock_z3_unknown():
    """Set up mock z3 where the first solver returns 'unknown' (timeout)."""
    mock = _make_mock_z3()
    factory = _SolverFactory()
    factory.add_check_results("unknown")
    mock.Solver = factory
    with patch.dict(sys.modules, {"z3": mock}):
        yield mock


@pytest.fixture
def mock_z3_insufficient_candidates():
    """Set up mock z3: orig unsat, all diagnostics also unsat -> insufficient_candidates.

    Each add_check_results creates one solver with its own result sequence.
    Solver 1 (original check) -> unsat
    Solver 2 (budget diag) -> unsat

    child_friendly_required=False and no dietary restrictions -> no more diag solvers.
    Both diagnostics return unsat -> no specific reason found -> insufficient_candidates.
    """
    mock = _make_mock_z3()
    factory = _SolverFactory()
    factory.add_check_results("unsat")   # solver 1: original feasibility
    factory.add_check_results("unsat")   # solver 2: budget diagnostic
    mock.Solver = factory
    with patch.dict(sys.modules, {"z3": mock}):
        yield mock


@pytest.fixture
def mock_z3_infeasible_dietary():
    """Set up mock z3: orig unsat, budget diag unsat, child diag unsat (skipped), dietary diag sat."""
    mock = _make_mock_z3()
    factory = _SolverFactory()
    # orig unsat, budget diag unsat, child diag not run (child_friendly_required=False), dietary diag sat
    factory.add_check_results("unsat", "unsat", "sat")
    mock.Solver = factory
    with patch.dict(sys.modules, {"z3": mock}):
        yield mock


# ===========================================================================
# Tests
# ===========================================================================


class TestZ3VerifierTool:
    """Tests for Z3VerifierTool."""

    # -- Metadata -----------------------------------------------------------

    def test_tool_metadata(self):
        """Tool exposes correct name, is_read_only, cost_model, and args_schema."""
        tool = Z3VerifierTool()
        assert tool.name == "z3_verify_feasibility"
        assert tool.is_read_only is True
        assert tool.cost_model == "free"
        assert tool.args_schema is not None
        assert tool.args_schema == Z3VerifierInput

    # -- Positive: feasible ------------------------------------------------

    @pytest.mark.asyncio
    async def test_feasible_basic(self, mock_z3_feasible):
        """3 activities + 2 restaurants within budget returns feasible=True."""
        tool = Z3VerifierTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
        )
        assert result.success is True
        assert result.data["feasible"] is True
        assert result.data["solver"] == "z3"

    # -- Negative: infeasible ----------------------------------------------

    @pytest.mark.asyncio
    async def test_infeasible_budget(self, mock_z3_infeasible_budget):
        """Budget=1 returns feasible=False with budget_too_low reason."""
        tool = Z3VerifierTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=1,
        )
        assert result.success is True
        assert result.data["feasible"] is False
        assert result.data["solver"] == "z3"
        assert "budget_too_low" in result.data.get("reasons", [])

    @pytest.mark.asyncio
    async def test_infeasible_child_friendly(self, mock_z3_infeasible_child):
        """child_friendly_required and no child-friendly options yields feasible=False."""
        no_cf_activities = [{**a, "child_friendly": False} for a in _ACTIVITIES]
        no_cf_restaurants = [{**r, "child_friendly": False} for r in _RESTAURANTS]
        tool = Z3VerifierTool()
        result = await tool._arun(
            activities=no_cf_activities,
            restaurants=no_cf_restaurants,
            budget=500,
            child_friendly_required=True,
        )
        assert result.success is True
        assert result.data["feasible"] is False
        assert "child_friendly_too_restrictive" in result.data.get("reasons", [])

    @pytest.mark.asyncio
    async def test_infeasible_insufficient_candidates(self, mock_z3_insufficient_candidates):
        """When no specific cause can be diagnosed, reason is insufficient_candidates."""
        tool = Z3VerifierTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=1,
        )
        assert result.success is True
        assert result.data["feasible"] is False
        assert "insufficient_candidates" in result.data.get("reasons", [])

    @pytest.mark.asyncio
    async def test_infeasible_dietary_restrictions(self, mock_z3_infeasible_dietary):
        """Dietary restrictions with no matching options yields dietary_too_restrictive reason."""
        tool = Z3VerifierTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
            dietary_restrictions=["vegan"],
        )
        assert result.success is True
        assert result.data["feasible"] is False
        assert "dietary_too_restrictive" in result.data.get("reasons", [])

    # -- Negative: empty candidates ----------------------------------------

    @pytest.mark.asyncio
    async def test_empty_candidates(self):
        """Empty activities or restaurants returns an error ToolResult."""
        tool = Z3VerifierTool()

        result = await tool._arun(activities=[], restaurants=_RESTAURANTS.copy())
        assert result.success is False
        assert "error" in result.data

        result = await tool._arun(activities=_ACTIVITIES.copy(), restaurants=[])
        assert result.success is False
        assert "error" in result.data

        result = await tool._arun(activities=[], restaurants=[])
        assert result.success is False
        assert "error" in result.data

    # -- Edge case: z3 not installed ---------------------------------------

    @pytest.mark.asyncio
    async def test_z3_not_installed(self):
        """When z3 is not importable, returns an error with install instructions."""
        tool = Z3VerifierTool()
        # Remove z3 from sys.modules and patch import to fail
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "z3":
                raise ImportError("No module named 'z3'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Also make sure z3 is not cached
            sys.modules.pop("z3", None)
            result = await tool._arun(
                activities=_ACTIVITIES.copy(),
                restaurants=_RESTAURANTS.copy(),
                budget=500,
            )

        assert result.success is False
        assert "z3-solver not installed" in result.data["error"]

    # -- Edge case: unknown result (timeout) --------------------------------

    @pytest.mark.asyncio
    async def test_z3_unknown_result(self, mock_z3_unknown):
        """When z3 returns unknown (timeout), feasible=None is returned."""
        tool = Z3VerifierTool()
        result = await tool._arun(
            activities=_ACTIVITIES.copy(),
            restaurants=_RESTAURANTS.copy(),
            budget=500,
        )
        assert result.success is True
        assert result.data["feasible"] is None
        assert "timeout" in result.data.get("reason", "").lower() or "unknown" in result.data.get("reason", "")

    # -- Compensation -------------------------------------------------------

    def test_compensation_is_noop(self):
        """compensation() returns a no-op CompensationAction."""
        tool = Z3VerifierTool()
        action = tool.compensation(args={}, result=MagicMock(spec=ToolResult))
        assert isinstance(action, CompensationAction)
        assert action.action_id == "z3_noop"
        assert action.tool_name == "z3_verify_feasibility"
        assert "no-op" in action.description.lower()

    # -- Schema -------------------------------------------------------------

    def test_args_schema_validates_positive_guest_count(self):
        """Z3VerifierInput enforces guest_count >= 1."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Z3VerifierInput(guest_count=0)

    def test_args_schema_defaults(self):
        """Z3VerifierInput provides sensible defaults."""
        schema = Z3VerifierInput()
        assert schema.budget == 500
        assert schema.guest_count == 2
        assert schema.child_friendly_required is False
        assert schema.dietary_restrictions == []
