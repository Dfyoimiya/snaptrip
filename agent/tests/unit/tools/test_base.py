"""Tests for SmartDayBaseTool and ToolResult."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self):
        """A basic success result can be created."""
        r = ToolResult(success=True, data={"msg": "ok"})
        assert r.success is True
        assert r.data == {"msg": "ok"}
        assert r.cost_cny == 0.0
        assert r.latency_ms == 0
        assert r.idempotency_key == ""

    def test_failure_result(self):
        """A basic failure result can be created."""
        r = ToolResult(success=False, data={"error": "failed"})
        assert r.success is False
        assert r.data["error"] == "failed"

    def test_with_cost_and_latency(self):
        """ToolResult can carry cost and latency."""
        r = ToolResult(
            success=True,
            data={"result": "done"},
            cost_cny=15.50,
            latency_ms=230,
            idempotency_key="idem-123",
        )
        assert r.cost_cny == 15.50
        assert r.latency_ms == 230
        assert r.idempotency_key == "idem-123"

    def test_mutable_fields(self):
        """ToolResult fields can be mutated after creation."""
        r = ToolResult(success=True, data={})
        r.latency_ms = 500
        r.cost_cny = 10.0
        assert r.latency_ms == 500
        assert r.cost_cny == 10.0


class TestSmartDayBaseTool:
    """Tests for SmartDayBaseTool base class."""

    def test_default_fields(self):
        """Base tool has default values for is_read_only, cost_model, tool_timeout."""

        class SampleTool(SmartDayBaseTool):
            name: str = "sample"
            description: str = "A sample tool."

            def compensation(self, args, result):
                raise NotImplementedError

            async def _arun(self, **kwargs):
                return ToolResult(success=True, data={})

        tool = SampleTool()
        assert tool.is_read_only is False
        assert tool.cost_model == "free"
        assert tool.tool_timeout == 5.0

    def test_idem_key_deterministic(self):
        """_idem_key produces the same hash for the same args."""

        class SampleTool(SmartDayBaseTool):
            name: str = "sample"
            description: str = "Sample."

            def compensation(self, args, result):
                raise NotImplementedError

            async def _arun(self, **kwargs):
                return ToolResult(success=True, data={})

        tool = SampleTool()
        key1 = tool._idem_key({"a": 1, "b": 2})
        key2 = tool._idem_key({"a": 1, "b": 2})
        assert key1 == key2
        assert len(key1) == 16

    def test_idem_key_different_for_different_args(self):
        """_idem_key produces different hashes for different args."""

        class SampleTool(SmartDayBaseTool):
            name: str = "sample"
            description: str = "Sample."

            def compensation(self, args, result):
                raise NotImplementedError

            async def _arun(self, **kwargs):
                return ToolResult(success=True, data={})

        tool = SampleTool()
        key1 = tool._idem_key({"a": 1})
        key2 = tool._idem_key({"a": 2})
        assert key1 != key2

    def test_noop_compensation(self):
        """_noop_compensation returns a CompensationAction for read-only tools."""

        class SampleTool(SmartDayBaseTool):
            name: str = "sample"
            description: str = "Sample."

            def compensation(self, args, result):
                raise NotImplementedError

            async def _arun(self, **kwargs):
                return ToolResult(success=True, data={})

        tool = SampleTool()
        action = tool._noop_compensation(action_id="noop-1", tool_name="sample")
        assert action.action_id == "noop-1"
        assert action.tool_name == "sample"
        assert action.description == "No-op compensation (read-only tool)"

    @pytest.mark.asyncio
    async def test_noop_compensation_execute(self):
        """No-op compensation executes without error."""

        class SampleTool(SmartDayBaseTool):
            name: str = "sample"
            description: str = "Sample."

            def compensation(self, args, result):
                raise NotImplementedError

            async def _arun(self, **kwargs):
                return ToolResult(success=True, data={})

        tool = SampleTool()
        action = tool._noop_compensation("noop-1", "sample")
        await action.execute()  # Should not raise

    @pytest.mark.asyncio
    async def test_ainvoke_wraps_non_toolresult(self):
        """ainvoke wraps non-ToolResult outputs in ToolResult."""

        class SampleTool(SmartDayBaseTool):
            name: str = "sample"
            description: str = "Sample."

            def compensation(self, args, result):
                raise NotImplementedError

            async def _arun(self, **kwargs):
                return {"plain": "dict"}

        tool = SampleTool()
        result = await tool.ainvoke({"key": "val"})
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == {"result": {"plain": "dict"}}

    @pytest.mark.asyncio
    async def test_ainvoke_passes_through_toolresult(self):
        """ainvoke passes through already-wrapped ToolResult."""

        class SampleTool(SmartDayBaseTool):
            name: str = "sample"
            description: str = "Sample."

            def compensation(self, args, result):
                raise NotImplementedError

            async def _arun(self, **kwargs):
                return ToolResult(success=True, data={"custom": True}, cost_cny=5.0)

        tool = SampleTool()
        result = await tool.ainvoke({"key": "val"})
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == {"custom": True}
        assert result.cost_cny == 5.0

    def test_compensation_abstract_raises(self):
        """compensation() raises NotImplementedError if not overridden."""

        class BadTool(SmartDayBaseTool):
            name: str = "bad"
            description: str = "Bad tool."

            async def _arun(self, **kwargs):
                return ToolResult(success=True, data={})

        tool = BadTool()
        with pytest.raises(NotImplementedError):
            tool.compensation({}, ToolResult(success=True, data={}))
