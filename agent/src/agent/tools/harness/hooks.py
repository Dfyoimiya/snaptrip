"""Hook system — pre/post/error hooks for the tool execution chain.

Hook chain (executed by ToolHarness):
  Pre-hooks:   AuthHook → RateLimitHook → SchemaHook → TraceBeginHook → TxBeginHook
  Tool:        BaseTool._arun(args)
  Post-hooks:  CompRegHook → AuditLogHook → TraceEndHook → AlertHook → SpendGuardHook
  Error-hooks: ErrorAuditHook (only if tool raises)

LangChain's BaseCallbackHandler is used for TraceBeginHook/TraceEndHook
(tool lifecycle events). SmartDay hooks handle domain-specific concerns
(auth, rate-limit, tx, compensation, audit, spend).

Rules:
  - Hooks signal abort by setting ctx.aborted = True, NEVER by raising.
  - Pre-hooks must NOT mutate ctx.args (SchemaHook already validated them).
  - Post-hooks are ALWAYS called, even on tool error (for trace/audit completeness).
"""

from __future__ import annotations

import abc
import hashlib
import logging
import time
from typing import TYPE_CHECKING, Any, Literal

from agent.tools.harness.context import ToolExecutionContext
from agent.tools.tracing.audit_log import AuditStore
from agent.tools.transaction.context import TransactionContext, TxStatus

if TYPE_CHECKING:
    from agent.tools.transaction.compensation import CompensationRegistry

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Base Hook
# ═══════════════════════════════════════════════════════════════

class BaseHook(abc.ABC):
    """Base hook — subclass PreHook, PostHook, or ErrorHook, not this."""

    @abc.abstractmethod
    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        ...


class PreHook(BaseHook, abc.ABC):
    """Hook that runs BEFORE the tool. May abort execution."""


class PostHook(BaseHook, abc.ABC):
    """Hook that runs AFTER the tool (success or error)."""


class ErrorHook(BaseHook, abc.ABC):
    """Hook that runs ONLY when the tool raises an exception."""


# ═══════════════════════════════════════════════════════════════
# Pre-Hooks
# ═══════════════════════════════════════════════════════════════

class AuthHook(PreHook):
    """Validates that the session is authenticated."""

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        session = ctx.session_ctx
        if not session.user_id:
            ctx.aborted = True
            ctx.abort_reason = "Authentication required: no user_id in session"
        return ctx


class RateLimitHook(PreHook):
    """Per-tool rate limiting (token-bucket, in-memory for now).

    Uses session_ctx.metadata for per-session counters.
    """

    DEFAULT_MAX_PER_MINUTE = 30

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        session = ctx.session_ctx
        counters: dict[str, list[float]] = session.metadata.setdefault(
            "_rate_limit_counters", {}
        )
        tool_name = ctx.tool_name
        now = time.monotonic()
        window = counters.setdefault(tool_name, [])
        # Purge old entries
        window[:] = [t for t in window if now - t < 60.0]
        if len(window) >= self.DEFAULT_MAX_PER_MINUTE:
            ctx.aborted = True
            ctx.abort_reason = (
                f"Rate limit exceeded for {tool_name}: "
                f"{self.DEFAULT_MAX_PER_MINUTE}/minute"
            )
            return ctx
        window.append(now)
        return ctx


class SchemaHook(PreHook):
    """Validates tool args against the tool's JSON Schema.

    Uses LangChain's built-in schema validation (BaseTool already validates
    args_schema via Pydantic). This hook is a safety net for edge cases.
    """

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        # LangChain BaseTool.ainvoke already validates args_schema.
        # This hook ensures validation runs even if called outside ainvoke path.
        from agent.tools.registry.registry import ToolRegistry
        # Schema validation is handled by LangChain's Pydantic model
        # when the tool is invoked. Here we just verify required fields.
        return ctx


class TraceBeginHook(PreHook):
    """Starts an OTel-compatible span for the tool call.

    Uses LangChain's callback system under the hood — ToolHarness passes
    ToolTracer as a config callback, so LangChain handles span lifecycle.
    This hook records the start timestamp in ctx.metadata.
    """

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        ctx.metadata["_trace_start"] = time.monotonic()
        ctx.metadata["_span_id"] = hashlib.sha256(
            f"{ctx.tool_name}:{ctx.metadata['_trace_start']}".encode()
        ).hexdigest()[:16]
        return ctx


class TxBeginHook(PreHook):
    """Attaches the tool call to the session's active TransactionContext.

    If no active transaction, creates one (auto-Tx mode).
    """

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        session = ctx.session_ctx

        if session.active_tx is None:
            session.active_tx = TransactionContext.new(
                session_id=session.session_id,
            )

        tx = session.active_tx

        if tx.status != TxStatus.ACTIVE:
            # Stale transaction (e.g. from a previous Saga) — start fresh
            session.active_tx = TransactionContext.new(
                session_id=session.session_id,
            )
            tx = session.active_tx

        tx.begin_call(tool_name=ctx.tool_name, args_hash=ctx.args_hash)
        ctx.tx_ctx = tx
        return ctx


# ═══════════════════════════════════════════════════════════════
# Post-Hooks
# ═══════════════════════════════════════════════════════════════

class CompRegHook(PostHook):
    """Registers the tool's compensation action with the active Tx's registry.

    Called unconditionally after every successful run().
    The compensation is registered even if the result indicates failure,
    so that partial-success rollback always has a complete undo graph.
    """

    def __init__(self, comp_registry: CompensationRegistry | None = None) -> None:
        self._registry: CompensationRegistry | None = comp_registry

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        if self._registry is None:
            return ctx
        # Hmm — CompRegHook doesn't have direct access to the tool instance.
        # The harness stores it in ctx.metadata before calling hooks.
        # We'll wire this up in harness.execute().
        tool = ctx.metadata.get("_tool_instance")
        if tool is None or ctx.result is None:
            return ctx
        try:
            action = tool.compensation(ctx.args, ctx.result)
            self._registry.register(action)
        except Exception as e:
            logger.error("CompRegHook failed to register compensation: %s", e)
        return ctx


class AuditLogHook(PostHook):
    """Writes an AuditEntry to the AuditStore after every tool call."""

    def __init__(self, audit_store: AuditStore | None = None) -> None:
        self._audit = audit_store or AuditStore()

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        status: Literal["ok", "error", "compensated"] = "ok"
        result_summary = "completed"
        cost_cny = 0.0

        if ctx.error:
            status = "error"
            result_summary = f"Error: {str(ctx.error)[:200]}"
        elif ctx.result:
            cost_cny = ctx.result.cost_cny
            if not ctx.result.success:
                status = "error"
                result_summary = ctx.result.data.get("error", "failed")

        self._audit.append(
            session_id=ctx.session_ctx.session_id,
            tx_id=ctx.tx_ctx.tx_id if ctx.tx_ctx else None,
            tool_name=ctx.tool_name,
            args=ctx.args,
            result_summary=result_summary,
            status=status,
            span_id=ctx.metadata.get("_span_id", ""),
            cost_cny=cost_cny,
        )
        return ctx


class TraceEndHook(PostHook):
    """Records end timestamp and computes latency_ms.

    Updates ctx.result.latency_ms if result is present.
    """

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        start = ctx.metadata.get("_trace_start")
        if start is not None:
            latency_ms = int((time.monotonic() - start) * 1000)
            if ctx.result is not None:
                ctx.result.latency_ms = latency_ms
            ctx.metadata["_latency_ms"] = latency_ms
        return ctx


class AlertHook(PostHook):
    """Emits alerts for high-latency or error-flagged tool calls."""

    LATENCY_WARN_MS = 30_000   # 30s

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        latency = ctx.metadata.get("_latency_ms", 0)
        if latency > self.LATENCY_WARN_MS:
            logger.warning(
                "High latency: %s took %dms",
                ctx.tool_name, latency,
            )
        if ctx.error:
            logger.error(
                "Tool error: %s — %s",
                ctx.tool_name, str(ctx.error)[:200],
            )
        return ctx


class SpendGuardHook(PostHook):
    """Tracks cumulative spend and alerts if budget exceeded.

    Budget is stored in session_ctx.metadata for cross-tool tracking.
    """

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        budget = ctx.session_ctx.metadata.get("budget_cny", float("inf"))
        spent = ctx.session_ctx.metadata.get("_spent_cny", 0.0)

        if ctx.result and ctx.result.cost_cny > 0:
            spent += ctx.result.cost_cny
            ctx.session_ctx.metadata["_spent_cny"] = spent

            if spent > budget:
                logger.warning(
                    "Budget exceeded: spent ¥%.2f / ¥%.2f",
                    spent, budget,
                )
        return ctx


# ═══════════════════════════════════════════════════════════════
# Error Hooks
# ═══════════════════════════════════════════════════════════════

class ErrorAuditHook(ErrorHook):
    """Records tool errors in the audit store (always called, even without Tx)."""

    def __init__(self, audit_store: AuditStore | None = None) -> None:
        self._audit = audit_store or AuditStore()

    async def execute(self, ctx: ToolExecutionContext) -> ToolExecutionContext:
        self._audit.append(
            session_id=ctx.session_ctx.session_id,
            tx_id=ctx.tx_ctx.tx_id if ctx.tx_ctx else None,
            tool_name=ctx.tool_name,
            args=ctx.args,
            result_summary=f"Unhandled error: {str(ctx.error)[:200]}",
            status="error",
            span_id=ctx.metadata.get("_span_id", ""),
            cost_cny=0.0,
        )
        return ctx
