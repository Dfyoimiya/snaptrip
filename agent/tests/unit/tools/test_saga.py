"""Tests for SagaCoordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.tools.harness.context import SessionContext
from agent.tools.harness.harness import ToolHarness
from agent.tools.implementations.base import ToolResult
from agent.tools.transaction.saga import SagaCoordinator
from agent.tools.transaction.context import TxStatus


class TestSagaCoordinator:
    """Tests for SagaCoordinator 3-phase saga."""

    def _make_harness(self) -> ToolHarness:
        """Create a harness with no hooks for saga testing."""
        harness = ToolHarness()
        harness.pre_hooks = []
        harness.post_hooks = []
        harness.error_hooks = []
        return harness

    def _make_mock_tool(
        self, name: str, harness: ToolHarness,
        reserve_result: ToolResult | None = None,
        confirm_result: ToolResult | None = None,
    ) -> MagicMock:
        """Register a mock tool that returns different results for reserve/confirm."""
        mock = MagicMock()
        mock.name = name
        mock.is_read_only = False
        mock.cost_model = "mock"
        mock.args_schema = None
        mock.compensation = MagicMock(return_value=None)

        call_count = [0]

        async def _ainvoke(input_data, *args, **kwargs):
            call_count[0] += 1
            if input_data.get("reserve_only"):
                return reserve_result or ToolResult(success=True, data={"reserved": True})
            return confirm_result or ToolResult(success=True, data={"confirmed": True})

        mock.ainvoke = _ainvoke
        harness.register_tool(mock)
        return mock

    @pytest.mark.asyncio
    async def test_saga_full_success(self):
        """A simple saga with two steps that both succeed."""
        harness = self._make_harness()
        self._make_mock_tool("tool_a", harness)
        self._make_mock_tool("tool_b", harness)

        session = SessionContext(session_id="s1", user_id="u1")
        coordinator = SagaCoordinator()

        result = await coordinator.execute(
            harness=harness,
            session_ctx=session,
            steps=[
                {"tool_name": "tool_a", "args": {"item": "A"}},
                {"tool_name": "tool_b", "args": {"item": "B"}},
            ],
        )

        assert result["status"] == "done"
        assert len(result["results"]) == 4  # 2 reserve + 2 confirm
        assert result["rollback_failures"] == []

    @pytest.mark.asyncio
    async def test_saga_reserve_failure_triggers_rollback(self):
        """When a reserve fails, rollback is triggered before any confirm."""
        harness = self._make_harness()
        self._make_mock_tool("tool_a", harness, reserve_result=ToolResult(success=True, data={}))
        self._make_mock_tool("tool_b", harness, reserve_result=ToolResult(success=False, data={"error": "fail"}))
        self._make_mock_tool("tool_c", harness)

        session = SessionContext(session_id="s1", user_id="u1")
        coordinator = SagaCoordinator()

        result = await coordinator.execute(
            harness=harness,
            session_ctx=session,
            steps=[
                {"tool_name": "tool_a", "args": {}},
                {"tool_name": "tool_b", "args": {}},
                {"tool_name": "tool_c", "args": {}},
            ],
        )

        assert result["status"] == "failed"
        assert result["phase"] == "reserve"

    @pytest.mark.asyncio
    async def test_saga_confirm_failure_triggers_rollback(self):
        """When a confirm fails, rollback is triggered."""
        harness = self._make_harness()
        self._make_mock_tool("tool_a", harness,
            reserve_result=ToolResult(success=True, data={}),
            confirm_result=ToolResult(success=True, data={}),
        )
        self._make_mock_tool("tool_b", harness,
            reserve_result=ToolResult(success=True, data={}),
            confirm_result=ToolResult(success=False, data={"error": "confirm fail"}),
        )

        session = SessionContext(session_id="s1", user_id="u1")
        coordinator = SagaCoordinator()

        result = await coordinator.execute(
            harness=harness,
            session_ctx=session,
            steps=[
                {"tool_name": "tool_a", "args": {}},
                {"tool_name": "tool_b", "args": {}},
            ],
        )

        assert result["status"] == "failed"
        assert result["phase"] == "confirm"

    @pytest.mark.asyncio
    async def test_saga_sets_tx_committed_on_success(self):
        """Transaction is set to COMMITTED after successful saga."""
        harness = self._make_harness()
        self._make_mock_tool("tool_a", harness)

        session = SessionContext(session_id="s1", user_id="u1")
        coordinator = SagaCoordinator()

        result = await coordinator.execute(
            harness=harness,
            session_ctx=session,
            steps=[{"tool_name": "tool_a", "args": {}}],
        )

        assert result["status"] == "done"
        assert session.active_tx.status == TxStatus.COMMITTED

    @pytest.mark.asyncio
    async def test_saga_rolled_back_on_reserve_failure(self):
        """Transaction is ROLLED_BACK after reserve failure."""
        harness = self._make_harness()
        self._make_mock_tool("tool_a", harness)
        self._make_mock_tool("tool_b", harness, reserve_result=ToolResult(success=False, data={"error": "fail"}))

        session = SessionContext(session_id="s1", user_id="u1")
        coordinator = SagaCoordinator()

        result = await coordinator.execute(
            harness=harness,
            session_ctx=session,
            steps=[
                {"tool_name": "tool_a", "args": {}},
                {"tool_name": "tool_b", "args": {}},
            ],
        )

        assert result["status"] == "failed"
        assert session.active_tx.status == TxStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_saga_passes_reserve_only_flag(self):
        """Reserve phase adds reserve_only=True to args, confirm passes False."""
        harness = self._make_harness()

        captured_calls = []

        mock = MagicMock()
        mock.name = "my_tool"
        mock.is_read_only = False
        mock.cost_model = "mock"
        mock.args_schema = None
        mock.compensation = MagicMock(return_value=None)
        async def _capture(input_data, *args, **kwargs):
            captured_calls.append(dict(input_data))
            return ToolResult(success=True, data={})
        mock.ainvoke = _capture
        harness.register_tool(mock)

        session = SessionContext(session_id="s1", user_id="u1")
        coordinator = SagaCoordinator()

        await coordinator.execute(
            harness=harness,
            session_ctx=session,
            steps=[{"tool_name": "my_tool", "args": {"city": "北京"}}],
        )

        assert len(captured_calls) == 2
        # Reserve call
        assert captured_calls[0]["reserve_only"] is True
        assert captured_calls[0]["city"] == "北京"
        # Confirm call
        assert captured_calls[1]["reserve_only"] is False
        assert captured_calls[1]["city"] == "北京"
