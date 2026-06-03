"""ToolHarness — the ONLY call site for tool execution.

Every tool invocation flows through ToolHarness.execute():

  LLM (tool_use)
    → MCP Server (tools/list | tools/call)
      → ToolHarness.execute(name, args, session_ctx)
        → [pre-hook chain] AuthHook → RateLimitHook → TraceBeginHook → TxBeginHook
        → SmartDayBaseTool._arun(args)
        → [post-hook chain] CompRegHook → AuditLogHook → TraceEndHook → AlertHook → SpendGuardHook
      → return ToolResult
    → LLM receives structured result

Agent nodes never instantiate tools directly — they call harness.execute().
Hooks are the ONLY place for cross-cutting concerns.
Tools are the ONLY place for external I/O.

Boundary rules (CI-enforced):
  - harness/ must never import from implementations/
  - implementations/ must never import from harness/
  - transaction/ must never import from tracing/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_core.callbacks import BaseCallbackManager

from agent.tools.harness.context import SessionContext, ToolExecutionContext
from agent.tools.harness.hooks import (
    AlertHook,
    AuditLogHook,
    AuthHook,
    CompRegHook,
    ErrorAuditHook,
    ErrorHook,
    PostHook,
    PreHook,
    RateLimitHook,
    SpendGuardHook,
    TraceBeginHook,
    TraceEndHook,
    TxBeginHook,
)
from agent.tools.implementations.base import ToolResult
from agent.tools.registry.registry import ToolRegistry
from agent.tools.tracing.audit_log import AuditStore
from agent.tools.tracing.tracer import ToolTracer
from agent.tools.transaction.compensation import CompensationRegistry

logger = logging.getLogger(__name__)


@dataclass
class ToolHarness:
    """Singleton orchestrator for tool execution.

    Composes:
      - ToolRegistry (thread-safe tool lookup)
      - PreHook[] (auth, rate-limit, trace-begin, tx-begin)
      - PostHook[] (comp-reg, audit, trace-end, alert, spend-guard)
      - ErrorHook[] (error-audit)

    Configuration:
      - hooks can be replaced per-instance for testing.
      - audit_store is shared across hooks.
    """

    registry: ToolRegistry = field(default_factory=ToolRegistry)

    # Configurable hook instances (build with defaults; replace in tests)
    pre_hooks: list[PreHook] = field(default_factory=list)
    post_hooks: list[PostHook] = field(default_factory=list)
    error_hooks: list[ErrorHook] = field(default_factory=list)

    # Shared services
    audit_store: AuditStore = field(default_factory=AuditStore)

    def __post_init__(self) -> None:
        """Initialize default hook chain if not provided."""
        if not self.pre_hooks:
            self.pre_hooks = [
                AuthHook(),
                RateLimitHook(),
                TraceBeginHook(),
                TxBeginHook(),
            ]
        if not self.post_hooks:
            self.post_hooks = [
                CompRegHook(),
                AuditLogHook(self.audit_store),
                TraceEndHook(),
                AlertHook(),
                SpendGuardHook(),
            ]
        if not self.error_hooks:
            self.error_hooks = [
                ErrorAuditHook(self.audit_store),
            ]

    # ── Public API ──────────────────────────────────────────────────

    async def execute(
        self,
        *,
        tool_name: str,
        args: dict[str, Any],
        session_ctx: SessionContext,
        tx_ctx: Any = None,
    ) -> ToolResult:
        """Execute a tool through the full hook chain.

        This is the ONLY public entry point for tool execution.
        No agent node or service should call tool._arun() directly.

        Args:
            tool_name: Registered tool name (must exist in registry).
            args: Tool arguments (validated by SchemaHook).
            session_ctx: Per-session identity, keys, and active transaction.
            tx_ctx: Transaction context (overrides session.active_tx if provided).

        Returns:
            ToolResult with success/data/cost/latency.
        """
        # Look up tool
        try:
            tool = self.registry.get(tool_name)
        except KeyError as e:
            return ToolResult(
                success=False,
                data={"error": str(e)},
            )

        # Build per-call context
        ctx = ToolExecutionContext(
            tool_name=tool_name,
            args=dict(args),
            session_ctx=session_ctx,
            tx_ctx=session_ctx.active_tx if tx_ctx is None else tx_ctx,
        )
        # Store tool instance for hooks that need it (CompRegHook)
        ctx.metadata["_tool_instance"] = tool

        # ── Pre-hook chain ──────────────────────────────────────
        for hook in self.pre_hooks:
            try:
                ctx = await hook.execute(ctx)
            except Exception as e:
                logger.exception("Pre-hook %s raised exception: %s", type(hook).__name__, e)
                # Pre-hook exception = abort (rule: hooks must set ctx.aborted, not raise,
                # but we guard against buggy hooks)
                ctx.aborted = True
                ctx.abort_reason = f"Pre-hook {type(hook).__name__} error: {e}"

            if ctx.aborted:
                logger.warning(
                    "Tool call aborted by %s: %s",
                    type(hook).__name__, ctx.abort_reason,
                )
                return ToolResult(
                    success=False,
                    data={"error": ctx.abort_reason or "aborted"},
                )

        # ── Run tool ────────────────────────────────────────────
        try:
            raw_result = await tool.ainvoke(
                ctx.args,
                config={"callbacks": self._build_callbacks(ctx)},
            )
            if isinstance(raw_result, ToolResult):
                ctx.result = raw_result
            else:
                ctx.result = ToolResult(
                    success=True,
                    data={"result": raw_result},
                )
        except Exception as e:
            logger.exception("Tool %s raised exception", tool_name)
            ctx.error = e
            ctx.result = ToolResult(
                success=False,
                data={"error": f"{type(e).__name__}: {str(e)[:200]}"},
            )
            # Run error hooks
            for hook in self.error_hooks:
                try:
                    ctx = await hook.execute(ctx)
                except Exception as hook_exc:
                    logger.exception(
                        "Error hook %s failed: %s", type(hook).__name__, hook_exc,
                    )

        # ── Post-hook chain (ALWAYS runs, even on error) ────────
        for hook in self.post_hooks:
            try:
                ctx = await hook.execute(ctx)
            except Exception as e:
                logger.exception(
                    "Post-hook %s failed: %s", type(hook).__name__, e,
                )

        return ctx.result or ToolResult(success=False, data={"error": "no result"})

    # ── Convenience ─────────────────────────────────────────────

    def register_tool(self, tool: Any) -> None:
        """Register a tool instance in the registry."""
        self.registry.register(tool)

    def list_tools(self, strict: bool = False) -> list[dict]:
        """Return all tool manifests as OpenAI function-calling format."""
        return self.registry.list_openai_tools(strict=strict)

    # ── Internal ────────────────────────────────────────────────

    def _build_callbacks(self, ctx: ToolExecutionContext) -> list:
        """Build LangChain callback handlers for tracing.

        Uses ToolTracer (BaseCallbackHandler subclass) for
        on_tool_start/on_tool_end/on_tool_error lifecycle events.
        """
        tracer = ToolTracer(self.audit_store)
        return [tracer]
