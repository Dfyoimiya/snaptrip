"""Tests for ToolHarness — the main tool execution orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.tools.harness.context import SessionContext
from agent.tools.harness.harness import ToolHarness
from agent.tools.harness.hooks import PreHook, PostHook, ErrorHook
from agent.tools.implementations.base import ToolResult


class TestToolHarness:
    """Tests for ToolHarness orchestrator."""

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_error(self):
        """Calling execute with an unregistered tool returns error ToolResult."""
        harness = ToolHarness()
        session = SessionContext(session_id="s1", user_id="u1")
        result = await harness.execute(
            tool_name="nonexistent",
            args={},
            session_ctx=session,
        )
        assert result.success is False
        assert "nonexistent" in result.data["error"]

    @pytest.mark.asyncio
    async def test_execute_successful_tool(self):
        """A tool that succeeds returns a success ToolResult."""
        harness = ToolHarness()

        mock_tool = MagicMock()
        mock_tool.name = "my_tool"
        mock_tool.is_read_only = False
        mock_tool.cost_model = "free"
        mock_tool.args_schema = None
        mock_tool.compensation = MagicMock(return_value=None)
        mock_tool.ainvoke = AsyncMock(return_value=ToolResult(
            success=True, data={"result": "hello"}, cost_cny=0.0,
        ))
        harness.register_tool(mock_tool)

        session = SessionContext(session_id="s1", user_id="u1")
        result = await harness.execute(
            tool_name="my_tool",
            args={"input": "test"},
            session_ctx=session,
        )
        assert result.success is True
        assert result.data["result"] == "hello"

    @pytest.mark.asyncio
    async def test_execute_with_hooks(self):
        """Pre and post hooks are called in order."""
        harness = ToolHarness()

        hook_order: list[str] = []

        class TrackingPreHook(PreHook):
            async def execute(self, ctx):
                hook_order.append("pre")
                return ctx

        class TrackingPostHook(PostHook):
            async def execute(self, ctx):
                hook_order.append("post")
                return ctx

        harness.pre_hooks = [TrackingPreHook()]
        harness.post_hooks = [TrackingPostHook()]

        mock_tool = MagicMock()
        mock_tool.name = "t"
        mock_tool.is_read_only = False
        mock_tool.cost_model = "free"
        mock_tool.args_schema = None
        mock_tool.compensation = MagicMock(return_value=None)
        mock_tool.ainvoke = AsyncMock(return_value=ToolResult(success=True, data={}))
        harness.register_tool(mock_tool)

        session = SessionContext(session_id="s1", user_id="u1")
        await harness.execute(tool_name="t", args={}, session_ctx=session)

        assert hook_order == ["pre", "post"]

    @pytest.mark.asyncio
    async def test_tool_exception_runs_error_hooks(self):
        """When tool raises, error hooks execute."""
        harness = ToolHarness()
        error_hook_called = False

        class TestErrorHook(ErrorHook):
            async def execute(self, ctx):
                nonlocal error_hook_called
                error_hook_called = True
                return ctx

        harness.error_hooks = [TestErrorHook()]
        harness.pre_hooks = []
        harness.post_hooks = []

        mock_tool = MagicMock()
        mock_tool.name = "failing"
        mock_tool.is_read_only = False
        mock_tool.cost_model = "free"
        mock_tool.args_schema = None
        mock_tool.ainvoke = AsyncMock(side_effect=ValueError("boom"))
        harness.register_tool(mock_tool)

        session = SessionContext(session_id="s1", user_id="u1")
        result = await harness.execute(tool_name="failing", args={}, session_ctx=session)

        assert result.success is False
        assert "boom" in result.data["error"]
        assert error_hook_called is True

    @pytest.mark.asyncio
    async def test_post_hooks_run_even_on_tool_error(self):
        """Post hooks run even when the tool raises."""
        harness = ToolHarness()
        post_hook_called = False

        class TestPostHook(PostHook):
            async def execute(self, ctx):
                nonlocal post_hook_called
                post_hook_called = True
                return ctx

        harness.pre_hooks = []
        harness.post_hooks = [TestPostHook()]

        mock_tool = MagicMock()
        mock_tool.name = "failing"
        mock_tool.is_read_only = False
        mock_tool.cost_model = "free"
        mock_tool.args_schema = None
        mock_tool.ainvoke = AsyncMock(side_effect=ValueError("fail"))
        harness.register_tool(mock_tool)

        session = SessionContext(session_id="s1", user_id="u1")
        await harness.execute(tool_name="failing", args={}, session_ctx=session)
        assert post_hook_called is True

    @pytest.mark.asyncio
    async def test_pre_hook_abort_returns_error_result(self):
        """When a pre-hook aborts, an error ToolResult is returned immediately."""
        harness = ToolHarness()

        class AbortingPreHook(PreHook):
            async def execute(self, ctx):
                ctx.aborted = True
                ctx.abort_reason = "Aborted by test hook"
                return ctx

        harness.pre_hooks = [AbortingPreHook()]
        harness.post_hooks = []

        mock_tool = MagicMock()
        mock_tool.name = "t"
        mock_tool.is_read_only = False
        mock_tool.args_schema = None
        mock_tool.ainvoke = AsyncMock(return_value=ToolResult(success=True, data={}))
        harness.register_tool(mock_tool)

        session = SessionContext(session_id="s1", user_id="u1")
        result = await harness.execute(tool_name="t", args={}, session_ctx=session)

        assert result.success is False
        assert "Aborted by test hook" in result.data["error"]
        mock_tool.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_pre_hook_exception_is_caught_and_aborts(self):
        """If a pre-hook raises, it is caught and converted to abort."""
        harness = ToolHarness()

        class BuggyPreHook(PreHook):
            async def execute(self, ctx):
                raise RuntimeError("hook bug")

        harness.pre_hooks = [BuggyPreHook()]
        harness.post_hooks = []

        mock_tool = MagicMock()
        mock_tool.name = "t"
        mock_tool.is_read_only = False
        mock_tool.args_schema = None
        mock_tool.ainvoke = AsyncMock(return_value=ToolResult(success=True, data={}))
        harness.register_tool(mock_tool)

        session = SessionContext(session_id="s1", user_id="u1")
        result = await harness.execute(tool_name="t", args={}, session_ctx=session)

        assert result.success is False
        assert "BuggyPreHook" in result.data["error"]
        mock_tool.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_tool_convenience(self):
        """register_tool delegates to registry.register."""
        harness = ToolHarness()
        mock_tool = MagicMock()
        mock_tool.name = "convenience"
        mock_tool.description = "Desc."
        mock_tool.args_schema = None
        mock_tool.is_read_only = True
        mock_tool.cost_model = "free"

        harness.register_tool(mock_tool)
        retrieved = harness.registry.get("convenience")
        assert retrieved is mock_tool

    def test_list_tools_convenience(self):
        """list_tools returns OpenAI-compatible tool list."""
        harness = ToolHarness()
        mock_tool = MagicMock()
        mock_tool.name = "listed"
        mock_tool.description = "Listed. Use it."
        mock_tool.args_schema = None
        mock_tool.is_read_only = True
        mock_tool.cost_model = "free"
        harness.register_tool(mock_tool)

        tools = harness.list_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "listed"

    def test_default_hooks_initialized(self):
        """ToolHarness initializes default hooks when not provided."""
        harness = ToolHarness()
        assert len(harness.pre_hooks) > 0
        assert len(harness.post_hooks) > 0
        assert len(harness.error_hooks) > 0

    def test_custom_hooks_preserved(self):
        """Custom hooks provided at init are preserved."""
        class CustomPre(PreHook):
            async def execute(self, ctx):
                return ctx

        custom_pre = CustomPre()
        harness = ToolHarness(pre_hooks=[custom_pre])
        assert harness.pre_hooks == [custom_pre]
        assert len(harness.pre_hooks) == 1

    @pytest.mark.asyncio
    async def test_tool_returns_non_toolresult_is_wrapped(self):
        """If ainvoke returns non-ToolResult, it is wrapped."""
        harness = ToolHarness()

        mock_tool = MagicMock()
        mock_tool.name = "plain_return"
        mock_tool.is_read_only = False
        mock_tool.args_schema = None
        mock_tool.compensation = MagicMock(return_value=None)
        mock_tool.ainvoke = AsyncMock(return_value={"msg": "not wrapped"})
        harness.register_tool(mock_tool)

        session = SessionContext(session_id="s1", user_id="u1")
        result = await harness.execute(
            tool_name="plain_return", args={}, session_ctx=session,
        )

        assert result.success is True
        assert result.data["result"] == {"msg": "not wrapped"}
