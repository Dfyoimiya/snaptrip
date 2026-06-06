"""Tests for all pre/post/error hooks."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from agent.tools.harness.context import SessionContext, ToolExecutionContext
from agent.tools.harness.hooks import (
    AlertHook,
    AuditLogHook,
    AuthHook,
    CompRegHook,
    ErrorAuditHook,
    RateLimitHook,
    SchemaHook,
    SpendGuardHook,
    TraceBeginHook,
    TraceEndHook,
    TxBeginHook,
)
from agent.tools.implementations.base import ToolResult
from agent.tools.tracing.audit_log import AuditStore
from agent.tools.transaction.compensation import CompensationAction, CompensationRegistry
from agent.tools.transaction.context import TransactionContext, TxStatus


class TestAuthHook:
    """Tests for AuthHook."""

    @pytest.mark.asyncio
    async def test_auth_passes_with_user_id(self, exec_ctx: ToolExecutionContext):
        """AuthHook passes when user_id is present."""
        hook = AuthHook()
        result = await hook.execute(exec_ctx)
        assert result.aborted is False
        assert result.abort_reason is None

    @pytest.mark.asyncio
    async def test_auth_aborts_without_user_id(
        self, exec_ctx: ToolExecutionContext, session_ctx_unauthenticated: SessionContext,
    ):
        """AuthHook aborts when user_id is empty."""
        exec_ctx.session_ctx = session_ctx_unauthenticated
        hook = AuthHook()
        result = await hook.execute(exec_ctx)
        assert result.aborted is True
        assert "Authentication required" in result.abort_reason


class TestRateLimitHook:
    """Tests for RateLimitHook."""

    @pytest.mark.asyncio
    async def test_under_limit_passes(self, exec_ctx: ToolExecutionContext):
        """RateLimitHook passes when under the per-minute limit."""
        hook = RateLimitHook()
        result = await hook.execute(exec_ctx)
        assert result.aborted is False

    @pytest.mark.asyncio
    async def test_exceeds_limit_aborts(self, exec_ctx: ToolExecutionContext):
        """RateLimitHook aborts when over the per-minute limit."""
        hook = RateLimitHook()
        for _ in range(RateLimitHook.DEFAULT_MAX_PER_MINUTE + 1):
            ctx = await hook.execute(
                ToolExecutionContext(
                    tool_name=exec_ctx.tool_name,
                    args=exec_ctx.args,
                    session_ctx=exec_ctx.session_ctx,
                )
            )
        assert ctx.aborted is True
        assert "Rate limit exceeded" in ctx.abort_reason

    @pytest.mark.asyncio
    async def test_counters_per_tool_per_session(self):
        """Counters are segregated by tool name and session."""
        hook = RateLimitHook()
        session_a = SessionContext(session_id="s1", user_id="u1")
        session_b = SessionContext(session_id="s2", user_id="u2")

        # Exhaust tool_a on session_a
        ctx = ToolExecutionContext(tool_name="tool_a", args={}, session_ctx=session_a)
        for _ in range(RateLimitHook.DEFAULT_MAX_PER_MINUTE + 1):
            ctx = await hook.execute(ctx)
        assert ctx.aborted is True

        # Different tool, same session — should pass
        ctx2 = ToolExecutionContext(tool_name="tool_b", args={}, session_ctx=session_a)
        result = await hook.execute(ctx2)
        assert result.aborted is False

        # Same tool, different session — should pass
        ctx3 = ToolExecutionContext(tool_name="tool_a", args={}, session_ctx=session_b)
        result = await hook.execute(ctx3)
        assert result.aborted is False


class TestSchemaHook:
    """Tests for SchemaHook."""

    @pytest.mark.asyncio
    async def test_schema_hook_always_passes(self, exec_ctx: ToolExecutionContext):
        """SchemaHook always passes (validation is handled by LangChain)."""
        hook = SchemaHook()
        result = await hook.execute(exec_ctx)
        assert result.aborted is False


class TestTraceBeginHook:
    """Tests for TraceBeginHook."""

    @pytest.mark.asyncio
    async def test_sets_trace_start_and_span_id(self, exec_ctx: ToolExecutionContext):
        """TraceBeginHook sets _trace_start and _span_id metadata."""
        hook = TraceBeginHook()
        result = await hook.execute(exec_ctx)
        assert "_trace_start" in result.metadata
        assert isinstance(result.metadata["_trace_start"], float)
        assert "_span_id" in result.metadata
        assert len(result.metadata["_span_id"]) == 16

    @pytest.mark.asyncio
    async def test_span_id_is_deterministic(self, exec_ctx: ToolExecutionContext):
        """Span ID is deterministic for same tool_name and same time."""
        hook = TraceBeginHook()
        with patch("time.monotonic", return_value=1000.0):
            result1 = await hook.execute(
                ToolExecutionContext(tool_name="t", args={}, session_ctx=exec_ctx.session_ctx)
            )
        with patch("time.monotonic", return_value=1000.0):
            result2 = await hook.execute(
                ToolExecutionContext(tool_name="t", args={}, session_ctx=exec_ctx.session_ctx)
            )
        assert result1.metadata["_span_id"] == result2.metadata["_span_id"]


class TestTxBeginHook:
    """Tests for TxBeginHook."""

    @pytest.mark.asyncio
    async def test_creates_transaction_if_none(self, exec_ctx: ToolExecutionContext):
        """TxBeginHook creates a new TransactionContext when session has none."""
        assert exec_ctx.session_ctx.active_tx is None
        hook = TxBeginHook()
        result = await hook.execute(exec_ctx)
        assert result.session_ctx.active_tx is not None
        assert result.tx_ctx is result.session_ctx.active_tx
        assert result.tx_ctx.status == TxStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_uses_existing_active_transaction(
        self, exec_ctx: ToolExecutionContext, tx_ctx: TransactionContext,
    ):
        """TxBeginHook uses the existing active transaction."""
        assert tx_ctx.status == TxStatus.ACTIVE
        exec_ctx.session_ctx.active_tx = tx_ctx
        hook = TxBeginHook()
        result = await hook.execute(exec_ctx)
        assert result.tx_ctx is tx_ctx

    @pytest.mark.asyncio
    async def test_registers_call_in_transaction(self, exec_ctx: ToolExecutionContext):
        """The tool call is recorded in the transaction."""
        hook = TxBeginHook()
        result = await hook.execute(exec_ctx)
        assert len(result.tx_ctx.calls) == 1
        assert result.tx_ctx.calls[0].tool_name == "test_tool"

    @pytest.mark.asyncio
    async def test_aborts_if_transaction_committed(
        self, exec_ctx: ToolExecutionContext, tx_ctx: TransactionContext,
    ):
        """Aborts if existing tx is COMMITTED."""
        tx_ctx.status = TxStatus.COMMITTED
        exec_ctx.session_ctx.active_tx = tx_ctx
        hook = TxBeginHook()
        result = await hook.execute(exec_ctx)
        assert result.aborted is True

    @pytest.mark.asyncio
    async def test_aborts_if_transaction_rolling_back(
        self, exec_ctx: ToolExecutionContext, tx_ctx: TransactionContext,
    ):
        """Aborts if existing tx is ROLLING_BACK."""
        tx_ctx.status = TxStatus.ROLLING_BACK
        exec_ctx.session_ctx.active_tx = tx_ctx
        hook = TxBeginHook()
        result = await hook.execute(exec_ctx)
        assert result.aborted is True

    @pytest.mark.asyncio
    async def test_aborts_if_transaction_rolled_back(
        self, exec_ctx: ToolExecutionContext, tx_ctx: TransactionContext,
    ):
        """Aborts if existing tx is ROLLED_BACK."""
        tx_ctx.status = TxStatus.ROLLED_BACK
        exec_ctx.session_ctx.active_tx = tx_ctx
        hook = TxBeginHook()
        result = await hook.execute(exec_ctx)
        assert result.aborted is True


class TestCompRegHook:
    """Tests for CompRegHook."""

    @pytest.mark.asyncio
    async def test_registers_compensation(
        self, exec_ctx: ToolExecutionContext, comp_registry: CompensationRegistry,
    ):
        """CompRegHook registers compensation when tool and result exist."""
        hook = CompRegHook(comp_registry)
        exec_ctx.result = ToolResult(success=True, data={"order_id": "ord-123"})

        async def _cancel() -> None:
            pass

        tool = MagicMock()
        tool.name = "test_tool"
        tool.compensation.return_value = CompensationAction(
            action_id="cancel:ord-123", tool_name="test_tool",
            description="Cancel test", execute=_cancel,
        )
        exec_ctx.metadata["_tool_instance"] = tool

        result = await hook.execute(exec_ctx)
        assert result is exec_ctx
        assert len(comp_registry._actions) == 1

    @pytest.mark.asyncio
    async def test_noop_with_null_registry(self, exec_ctx: ToolExecutionContext):
        """CompRegHook does nothing when comp_registry is None."""
        hook = CompRegHook(comp_registry=None)
        result = await hook.execute(exec_ctx)
        assert result is exec_ctx

    @pytest.mark.asyncio
    async def test_noop_when_no_tool_instance(
        self, exec_ctx: ToolExecutionContext, comp_registry: CompensationRegistry,
    ):
        """CompRegHook does nothing when _tool_instance is missing."""
        hook = CompRegHook(comp_registry)
        exec_ctx.result = ToolResult(success=True, data={})
        result = await hook.execute(exec_ctx)
        assert len(comp_registry._actions) == 0

    @pytest.mark.asyncio
    async def test_handles_compensation_exception(
        self, exec_ctx: ToolExecutionContext, comp_registry: CompensationRegistry, caplog,
    ):
        """CompRegHook catches exceptions from tool.compensation()."""
        import logging
        caplog.set_level(logging.ERROR)
        hook = CompRegHook(comp_registry)
        exec_ctx.result = ToolResult(success=True, data={})
        tool = MagicMock()
        tool.name = "failing_tool"
        tool.compensation.side_effect = ValueError("compensation failed")
        exec_ctx.metadata["_tool_instance"] = tool

        result = await hook.execute(exec_ctx)
        assert result is exec_ctx
        assert "compensation failed" in caplog.text


class TestAuditLogHook:
    """Tests for AuditLogHook."""

    @pytest.mark.asyncio
    async def test_writes_ok_entry(self, exec_ctx: ToolExecutionContext, audit_store: AuditStore):
        """AuditLogHook writes an 'ok' entry on success."""
        hook = AuditLogHook(audit_store)
        exec_ctx.result = ToolResult(success=True, data={"result": "done"})
        exec_ctx.tx_ctx = TransactionContext.new(session_id="s1")
        exec_ctx.metadata["_span_id"] = "span-1"

        await hook.execute(exec_ctx)
        assert len(audit_store._entries) == 1
        entry = audit_store._entries[0]
        assert entry.status == "ok"
        assert entry.result_summary == "completed"

    @pytest.mark.asyncio
    async def test_writes_error_entry_on_exception(
        self, exec_ctx: ToolExecutionContext, audit_store: AuditStore,
    ):
        """AuditLogHook writes an 'error' entry when tool raised exception."""
        hook = AuditLogHook(audit_store)
        exec_ctx.error = ValueError("something broke")
        exec_ctx.metadata["_span_id"] = "span-2"

        await hook.execute(exec_ctx)
        assert len(audit_store._entries) == 1
        entry = audit_store._entries[0]
        assert entry.status == "error"
        assert "something broke" in entry.result_summary

    @pytest.mark.asyncio
    async def test_writes_error_entry_for_failed_result(
        self, exec_ctx: ToolExecutionContext, audit_store: AuditStore,
    ):
        """AuditLogHook writes 'error' when result.success is False."""
        hook = AuditLogHook(audit_store)
        exec_ctx.result = ToolResult(success=False, data={"error": "service down"})
        exec_ctx.metadata["_span_id"] = "span-3"

        await hook.execute(exec_ctx)
        assert len(audit_store._entries) == 1
        entry = audit_store._entries[0]
        assert entry.status == "error"
        assert "service down" in entry.result_summary

    @pytest.mark.asyncio
    async def test_tracks_cost(self, exec_ctx: ToolExecutionContext, audit_store: AuditStore):
        """AuditLogHook records cost_cny from result."""
        hook = AuditLogHook(audit_store)
        exec_ctx.result = ToolResult(success=True, data={}, cost_cny=12.50)
        exec_ctx.metadata["_span_id"] = "span-4"

        await hook.execute(exec_ctx)
        assert audit_store._entries[0].cost_cny == 12.50

    @pytest.mark.asyncio
    async def test_default_audit_store(self, exec_ctx: ToolExecutionContext):
        """AuditLogHook creates its own AuditStore if none provided."""
        hook = AuditLogHook()
        exec_ctx.result = ToolResult(success=True, data={})
        exec_ctx.metadata["_span_id"] = ""
        await hook.execute(exec_ctx)


class TestTraceEndHook:
    """Tests for TraceEndHook."""

    @pytest.mark.asyncio
    async def test_sets_latency_ms_on_result(self, exec_ctx: ToolExecutionContext):
        """TraceEndHook sets latency_ms on the result."""
        hook = TraceEndHook()
        exec_ctx.result = ToolResult(success=True, data={})
        exec_ctx.metadata["_trace_start"] = time.monotonic() - 0.5

        result = await hook.execute(exec_ctx)
        assert result.result.latency_ms >= 400

    @pytest.mark.asyncio
    async def test_noop_without_trace_start(self, exec_ctx: ToolExecutionContext):
        """If _trace_start is missing, nothing happens."""
        hook = TraceEndHook()
        exec_ctx.result = ToolResult(success=True, data={})
        result = await hook.execute(exec_ctx)
        assert result.result.latency_ms == 0

    @pytest.mark.asyncio
    async def test_noop_without_result(self, exec_ctx: ToolExecutionContext):
        """If result is None, no error raised."""
        hook = TraceEndHook()
        exec_ctx.metadata["_trace_start"] = time.monotonic() - 0.5
        result = await hook.execute(exec_ctx)
        assert result.metadata.get("_latency_ms") is not None


class TestAlertHook:
    """Tests for AlertHook."""

    @pytest.mark.asyncio
    async def test_no_warning_under_threshold(self, exec_ctx: ToolExecutionContext, caplog):
        """No warning logged when latency is under threshold."""
        import logging
        caplog.set_level(logging.WARNING)
        hook = AlertHook()
        exec_ctx.metadata["_latency_ms"] = 100

        await hook.execute(exec_ctx)
        assert "High latency" not in caplog.text

    @pytest.mark.asyncio
    async def test_warning_over_threshold(self, exec_ctx: ToolExecutionContext, caplog):
        """Warning logged when latency exceeds threshold."""
        import logging
        caplog.set_level(logging.WARNING)
        hook = AlertHook()
        exec_ctx.metadata["_latency_ms"] = 31_000

        await hook.execute(exec_ctx)
        assert "High latency" in caplog.text
        assert "test_tool" in caplog.text

    @pytest.mark.asyncio
    async def test_error_logged(self, exec_ctx: ToolExecutionContext, caplog):
        """Error logged when ctx.error is set."""
        import logging
        caplog.set_level(logging.ERROR)
        hook = AlertHook()
        exec_ctx.error = RuntimeError("Connection failed")

        await hook.execute(exec_ctx)
        assert "Tool error" in caplog.text
        assert "Connection failed" in caplog.text

    @pytest.mark.asyncio
    async def test_no_error_when_no_error(self, exec_ctx: ToolExecutionContext, caplog):
        import logging
        caplog.set_level(logging.ERROR)
        hook = AlertHook()
        exec_ctx.metadata["_latency_ms"] = 100

        await hook.execute(exec_ctx)
        assert "Tool error" not in caplog.text


class TestSpendGuardHook:
    """Tests for SpendGuardHook."""

    @pytest.mark.asyncio
    async def test_tracks_spend(self, exec_ctx: ToolExecutionContext):
        """SpendGuardHook accumulates cost_cny in session metadata."""
        hook = SpendGuardHook()
        exec_ctx.result = ToolResult(success=True, data={}, cost_cny=10.0)

        await hook.execute(exec_ctx)
        assert exec_ctx.session_ctx.metadata["_spent_cny"] == 10.0

    @pytest.mark.asyncio
    async def test_accumulates_multiple_calls(self, exec_ctx: ToolExecutionContext):
        """Multiple calls accumulate spend."""
        hook = SpendGuardHook()
        exec_ctx.result = ToolResult(success=True, data={}, cost_cny=5.0)
        await hook.execute(exec_ctx)
        exec_ctx.result = ToolResult(success=True, data={}, cost_cny=3.0)
        await hook.execute(exec_ctx)
        assert exec_ctx.session_ctx.metadata["_spent_cny"] == 8.0

    @pytest.mark.asyncio
    async def test_zero_cost_no_change(self, exec_ctx: ToolExecutionContext):
        """Zero-cost results start the accumulator at 0."""
        hook = SpendGuardHook()
        exec_ctx.result = ToolResult(success=True, data={}, cost_cny=0.0)

        await hook.execute(exec_ctx)
        assert exec_ctx.session_ctx.metadata.get("_spent_cny", 0.0) == 0.0

    @pytest.mark.asyncio
    async def test_budget_exceeded_warning(self, exec_ctx: ToolExecutionContext, caplog):
        """Warning logged when budget is exceeded."""
        import logging
        caplog.set_level(logging.WARNING)
        exec_ctx.session_ctx.metadata["budget_cny"] = 5.0
        hook = SpendGuardHook()
        exec_ctx.result = ToolResult(success=True, data={}, cost_cny=10.0)

        await hook.execute(exec_ctx)
        assert "Budget exceeded" in caplog.text


class TestErrorAuditHook:
    """Tests for ErrorAuditHook."""

    @pytest.mark.asyncio
    async def test_writes_error_entry(self, exec_ctx: ToolExecutionContext):
        """ErrorAuditHook writes an error audit entry."""
        hook = ErrorAuditHook()
        exec_ctx.error = ValueError("critical failure")

        await hook.execute(exec_ctx)
        store = hook._audit
        assert len(store._entries) == 1
        entry = store._entries[0]
        assert entry.status == "error"
        assert "critical failure" in entry.result_summary

    @pytest.mark.asyncio
    async def test_default_audit_store(self, exec_ctx: ToolExecutionContext):
        """ErrorAuditHook creates its own AuditStore if not provided."""
        hook = ErrorAuditHook()
        exec_ctx.error = ValueError("err")
        await hook.execute(exec_ctx)
        assert len(hook._audit._entries) == 1
