"""Tests for ToolTracer LangChain callback handler."""

from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock, patch

import pytest

from agent.tools.tracing.audit_log import AuditStore
from agent.tools.tracing.tracer import ToolTracer


class TestToolTracer:
    """Tests for ToolTracer."""

    def test_initialization(self, audit_store: AuditStore):
        """ToolTracer can be created with an audit store."""
        tracer = ToolTracer(audit_store)
        assert tracer._audit_store is audit_store
        assert tracer._active_spans == {}

    @pytest.mark.asyncio
    async def test_on_tool_start_creates_span(self, audit_store: AuditStore):
        """on_tool_start creates an active span."""
        tracer = ToolTracer(audit_store)
        run_id = uuid.uuid4()

        tracer.on_tool_start(
            serialized={"name": "test_tool"},
            input_str="test input",
            run_id=run_id,
            inputs={"lat": 39.9, "lng": 116.4},
        )

        assert str(run_id) in tracer._active_spans
        span = tracer._active_spans[str(run_id)]
        assert span["tool_name"] == "test_tool"
        assert span["inputs"] == {"lat": 39.9, "lng": 116.4}
        assert "start_ts" in span

    @pytest.mark.asyncio
    async def test_on_tool_end_writes_audit_entry(self, audit_store: AuditStore):
        """on_tool_end creates an audit entry and removes the span."""
        tracer = ToolTracer(audit_store)
        run_id = uuid.uuid4()

        tracer.on_tool_start(
            serialized={"name": "my_tool"},
            input_str="",
            run_id=run_id,
            inputs={"key": "val"},
        )

        # Mock output with cost_cny
        mock_result = MagicMock()
        mock_result.cost_cny = 12.50

        tracer.on_tool_end(output=mock_result, run_id=run_id)

        assert str(run_id) not in tracer._active_spans
        assert len(audit_store._entries) == 1
        entry = audit_store._entries[0]
        assert entry.tool_name == "my_tool"
        assert entry.status == "ok"
        assert entry.cost_cny == 12.50

    @pytest.mark.asyncio
    async def test_on_tool_end_without_cost_cny(self, audit_store: AuditStore):
        """on_tool_end defaults cost to 0.0 when output has no cost_cny."""
        tracer = ToolTracer(audit_store)
        run_id = uuid.uuid4()

        tracer.on_tool_start(
            serialized={"name": "free_tool"},
            input_str="",
            run_id=run_id,
            inputs={},
        )
        tracer.on_tool_end(output="plain string output", run_id=run_id)

        assert audit_store._entries[0].cost_cny == 0.0

    @pytest.mark.asyncio
    async def test_on_tool_error_writes_audit_entry(self, audit_store: AuditStore):
        """on_tool_error creates an error audit entry."""
        tracer = ToolTracer(audit_store)
        run_id = uuid.uuid4()

        tracer.on_tool_start(
            serialized={"name": "buggy_tool"},
            input_str="",
            run_id=run_id,
            inputs={},
        )

        tracer.on_tool_error(
            error=ValueError("something went wrong"),
            run_id=run_id,
        )

        assert str(run_id) not in tracer._active_spans
        assert len(audit_store._entries) == 1
        entry = audit_store._entries[0]
        assert entry.status == "error"
        assert "something went wrong" in entry.result_summary

    @pytest.mark.asyncio
    async def test_on_tool_end_ignores_unknown_span(self, audit_store: AuditStore):
        """on_tool_end with an unknown run_id is a no-op."""
        tracer = ToolTracer(audit_store)
        tracer.on_tool_end(output={}, run_id=uuid.uuid4())
        assert len(audit_store._entries) == 0

    @pytest.mark.asyncio
    async def test_on_tool_error_ignores_unknown_span(self, audit_store: AuditStore):
        """on_tool_error with an unknown run_id is a no-op."""
        tracer = ToolTracer(audit_store)
        tracer.on_tool_error(error=ValueError(), run_id=uuid.uuid4())
        assert len(audit_store._entries) == 0

    @pytest.mark.asyncio
    async def test_multiple_concurrent_spans(self, audit_store: AuditStore):
        """Multiple concurrent spans are tracked independently."""
        tracer = ToolTracer(audit_store)
        run_id_1 = uuid.uuid4()
        run_id_2 = uuid.uuid4()

        tracer.on_tool_start(serialized={"name": "tool_a"}, input_str="", run_id=run_id_1, inputs={})
        tracer.on_tool_start(serialized={"name": "tool_b"}, input_str="", run_id=run_id_2, inputs={})

        assert len(tracer._active_spans) == 2

        tracer.on_tool_end(output={}, run_id=run_id_1)
        assert len(tracer._active_spans) == 1
        assert str(run_id_1) not in tracer._active_spans
        assert str(run_id_2) in tracer._active_spans
