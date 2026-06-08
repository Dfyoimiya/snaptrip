"""Tool execution context — created per-call by ToolHarness, mutated by hooks.

Every tool call gets its own ToolExecutionContext.  Hooks read and mutate it
but MUST follow these rules:
  - Pre-hooks must NOT mutate ctx.args
  - Hooks signal abort by setting ctx.aborted = True, never by raising
  - ctx.metadata is a hook-private scratchpad (no cross-hook contract)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from agent.tools.implementations.base import ToolResult
from agent.tools.transaction.context import TransactionContext


@dataclass
class SessionContext:
    """Per-session context — created once for the lifetime of a plan execution.

    Holds the active transaction, API keys, and user identity.
    API keys come from session context, never from env in tool implementations.
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    amap_api_key: str = ""

    # Active transaction (set/cleared by TxBeginHook / SagaCoordinator)
    active_tx: TransactionContext | None = None

    # Custom data for hooks (e.g., rate-limit counters)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionContext:
    """Per-call execution context — created by ToolHarness before each tool call.

    Lifecycle:
      1. ToolHarness creates a fresh ToolExecutionContext
      2. Pre-hooks execute in order, each reading/mutating ctx
      3. If ctx.aborted → return ToolResult(success=False)
      4. Tool runs via ctx.tool.ainvoke(ctx.args)
      5. Post-hooks execute in order
      6. ToolResult returned to harness

    Fields mutated by hooks:
      - aborted / abort_reason  (set by pre-hooks to cancel execution)
      - tx_ctx                  (set by TxBeginHook)
      - result                  (set by harness after tool.run())
      - error                   (set by harness on tool exception)
      - metadata                (scratchpad for hooks, no contract between hooks)
    """

    # ── Immutable (set by harness at creation) ──
    tool_name: str
    args: dict[str, Any]
    session_ctx: SessionContext

    # ── Mutable (set by hooks) ──
    tx_ctx: TransactionContext | None = None
    result: ToolResult | None = None
    error: Exception | None = None
    aborted: bool = False
    abort_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def args_hash(self) -> str:
        """SHA-256 of args for audit (never stores raw PII in logs)."""
        import hashlib
        import json

        payload = json.dumps(self.args, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
