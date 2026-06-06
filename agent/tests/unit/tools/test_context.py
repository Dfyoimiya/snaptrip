"""Tests for SessionContext and ToolExecutionContext."""

from __future__ import annotations

import pytest

from agent.tools.harness.context import SessionContext, ToolExecutionContext
from agent.tools.transaction.context import TransactionContext


class TestSessionContext:
    """Tests for SessionContext."""

    def test_default_factory_creates_session_id(self):
        """SessionContext auto-generates a session_id."""
        ctx = SessionContext()
        assert ctx.session_id is not None
        assert len(ctx.session_id) > 0

    def test_unique_session_ids(self):
        """Two contexts get different session_ids."""
        ctx1 = SessionContext()
        ctx2 = SessionContext()
        assert ctx1.session_id != ctx2.session_id

    def test_with_user_id(self):
        """SessionContext carries the provided user_id."""
        ctx = SessionContext(user_id="user-abc")
        assert ctx.user_id == "user-abc"

    def test_with_amap_api_key(self):
        """SessionContext carries the provided amap_api_key."""
        ctx = SessionContext(amap_api_key="my-key")
        assert ctx.amap_api_key == "my-key"

    def test_empty_user_id(self):
        """SessionContext with empty user_id is valid (auth is hook concern)."""
        ctx = SessionContext(user_id="")
        assert ctx.user_id == ""

    def test_active_tx_defaults_to_none(self):
        """active_tx is None when not set."""
        ctx = SessionContext()
        assert ctx.active_tx is None

    def test_active_tx_can_be_set(self, tx_ctx: TransactionContext):
        """Active transaction can be assigned."""
        ctx = SessionContext()
        ctx.active_tx = tx_ctx
        assert ctx.active_tx is tx_ctx

    def test_metadata_starts_empty(self):
        """metadata dict starts empty."""
        ctx = SessionContext()
        assert ctx.metadata == {}

    def test_metadata_is_mutable(self):
        """metadata dict can be mutated."""
        ctx = SessionContext()
        ctx.metadata["key"] = "value"
        assert ctx.metadata["key"] == "value"


class TestToolExecutionContext:
    """Tests for ToolExecutionContext."""

    def test_create_basic(self, session_ctx: SessionContext):
        """A minimal execution context can be created."""
        ctx = ToolExecutionContext(
            tool_name="test_tool",
            args={"lat": 39.9},
            session_ctx=session_ctx,
        )
        assert ctx.tool_name == "test_tool"
        assert ctx.args == {"lat": 39.9}
        assert ctx.session_ctx is session_ctx

    def test_defaults(self, session_ctx: SessionContext):
        """Mutable fields have sensible defaults."""
        ctx = ToolExecutionContext(
            tool_name="t", args={}, session_ctx=session_ctx,
        )
        assert ctx.tx_ctx is None
        assert ctx.result is None
        assert ctx.error is None
        assert ctx.aborted is False
        assert ctx.abort_reason is None
        assert ctx.metadata == {}

    def test_args_hash_deterministic(self, session_ctx: SessionContext):
        """Same args produce the same args_hash."""
        ctx1 = ToolExecutionContext(
            tool_name="t", args={"a": 1, "b": 2}, session_ctx=session_ctx,
        )
        ctx2 = ToolExecutionContext(
            tool_name="t", args={"a": 1, "b": 2}, session_ctx=session_ctx,
        )
        assert ctx1.args_hash == ctx2.args_hash

    def test_args_hash_changes_on_different_args(self, session_ctx: SessionContext):
        """Different args produce different args_hash."""
        ctx1 = ToolExecutionContext(
            tool_name="t", args={"a": 1}, session_ctx=session_ctx,
        )
        ctx2 = ToolExecutionContext(
            tool_name="t", args={"a": 2}, session_ctx=session_ctx,
        )
        assert ctx1.args_hash != ctx2.args_hash

    def test_args_hash_key_order_independent(self, session_ctx: SessionContext):
        """args_hash is independent of dict key ordering."""
        ctx1 = ToolExecutionContext(
            tool_name="t", args={"lat": 1.0, "lng": 2.0}, session_ctx=session_ctx,
        )
        ctx2 = ToolExecutionContext(
            tool_name="t", args={"lng": 2.0, "lat": 1.0}, session_ctx=session_ctx,
        )
        assert ctx1.args_hash == ctx2.args_hash

    def test_abort_flow(self, session_ctx: SessionContext):
        """Setting aborted and abort_reason works."""
        ctx = ToolExecutionContext(
            tool_name="t", args={}, session_ctx=session_ctx,
        )
        ctx.aborted = True
        ctx.abort_reason = "Rate limit exceeded"
        assert ctx.aborted is True
        assert ctx.abort_reason == "Rate limit exceeded"

    def test_result_assignment(self, session_ctx: SessionContext):
        """result can be set after execution."""
        from agent.tools.implementations.base import ToolResult
        ctx = ToolExecutionContext(
            tool_name="t", args={}, session_ctx=session_ctx,
        )
        result = ToolResult(success=True, data={"msg": "done"})
        ctx.result = result
        assert ctx.result is result

    def test_tx_ctx_assignment(self, session_ctx: SessionContext, tx_ctx: TransactionContext):
        """tx_ctx can be set."""
        ctx = ToolExecutionContext(
            tool_name="t", args={}, session_ctx=session_ctx,
        )
        ctx.tx_ctx = tx_ctx
        assert ctx.tx_ctx is tx_ctx

    def test_error_assignment(self, session_ctx: SessionContext):
        """error can be set."""
        ctx = ToolExecutionContext(
            tool_name="t", args={}, session_ctx=session_ctx,
        )
        exc = ValueError("test error")
        ctx.error = exc
        assert ctx.error is exc
