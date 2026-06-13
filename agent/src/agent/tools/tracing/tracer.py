"""ToolTracer — LangChain-compatible callback for tool lifecycle tracing.

Wraps LangChain's BaseCallbackHandler to emit tool_start / tool_end / tool_error
events without reinventing observability primitives.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from agent.tools.tracing.audit_log import AuditStore

logger = logging.getLogger(__name__)


class ToolTracer(BaseCallbackHandler):
    """LangChain callback for tool lifecycle observability.

    Integrates with AuditStore for hash-chain audit logging.
    Each tool call gets a unique span_id for tracing correlation.

    Usage:
        tracer = ToolTracer(audit_store)
        tool.invoke(args, config={"callbacks": [tracer]})
    """

    def __init__(self, audit_store: AuditStore | None = None) -> None:
        super().__init__()
        self._audit_store = audit_store or AuditStore()
        self._active_spans: dict[str, dict[str, Any]] = {}

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Record tool start event."""
        span = {
            "span_id": str(run_id),
            "tool_name": serialized.get("name", "unknown"),
            "start_ts": time.monotonic(),
            "inputs": inputs or {},
        }
        self._active_spans[str(run_id)] = span
        logger.debug("Tool start: %s (span=%s)", span["tool_name"], span["span_id"])

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Record tool end event with audit entry."""
        span = self._active_spans.pop(str(run_id), None)
        if span is None:
            return

        latency_ms = int((time.monotonic() - span["start_ts"]) * 1000)
        tool_name = span["tool_name"]

        # Extract cost and status from ToolResult if available
        cost_cny = 0.0
        if hasattr(output, "cost_cny"):
            cost_cny = output.cost_cny

        self._audit_store.append(
            session_id=span.get("session_id", ""),
            tx_id=span.get("tx_id"),
            tool_name=tool_name,
            args=span.get("inputs", {}),
            result_summary=f"{tool_name} completed in {latency_ms}ms",
            status="ok",
            span_id=span["span_id"],
            cost_cny=cost_cny,
        )
        logger.debug(
            "Tool end: %s (span=%s, %dms)", tool_name, span["span_id"], latency_ms
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Record tool error event with audit entry."""
        span = self._active_spans.pop(str(run_id), None)
        if span is None:
            return

        self._audit_store.append(
            session_id=span.get("session_id", ""),
            tx_id=span.get("tx_id"),
            tool_name=span["tool_name"],
            args=span.get("inputs", {}),
            result_summary=f"Error: {str(error)[:200]}",
            status="error",
            span_id=span["span_id"],
            cost_cny=0.0,
        )
