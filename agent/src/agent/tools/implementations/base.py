"""SmartDay BaseTool — extends LangChain BaseTool with SmartDay-specific contracts.

Every tool in the system inherits from this class, NOT from BaseTool directly.
Adds: compensation, cost tracking, read-only marking, idempotency key generation.

Rules (CI-enforced):
  - implementations/ must never import from harness/
  - Every file in implementations/ exports exactly one SmartDayBaseTool subclass
  - Every tool must return a non-None compensation action
  - Pre-hooks must NOT mutate ctx.args
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import BaseTool

from agent.tools.transaction.compensation import CompensationAction


@dataclass
class ToolResult:
    """Canonical return type for all SmartDay tool invocations.

    Returned by ToolHarness.execute() after the full hook chain.
    """

    success: bool
    data: dict[str, Any]
    cost_cny: float = 0.0
    latency_ms: int = 0
    idempotency_key: str = ""


class SmartDayBaseTool(BaseTool):
    """Extended BaseTool for SmartDay domain-specific contracts.

    Additional fields vs LangChain BaseTool:
      - is_read_only: True for search/geocode tools (no monetary side effects)
      - cost_model: "free" | "per_call:¥0.001" | "mock"
      - tool_timeout: per-tool timeout seconds (POI=5s, routing=8s, payment=15s)

    Additional methods:
      - compensation(): Returns a CompensationAction for rollback.
      - _idem_key(): Generate a deterministic idempotency key from args.

    NOTE: Subclasses MUST NOT use @dataclass — LangChain BaseTool is a Pydantic
    model, and mixing dataclass/Pydantic __init__ breaks field defaults.
    Instead, set class-level attributes or use model_fields override.
    """

    is_read_only: bool = False
    cost_model: str = "free"
    tool_timeout: float = 5.0

    class Config:
        # Allow arbitrary fields (Pydantic v1 compat)
        extra = "allow"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Sync wrapper — delegates to _arun.

        All SmartDay tools are async-first. This satisfies LangChain's
        abstract _run contract but should not be called directly.
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._arun(*args, **kwargs))
        raise RuntimeError(
            f"Cannot call sync _run() on async tool '{self.name}' "
            "from within a running event loop. Use ainvoke() instead."
        )

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        """Return a CompensationAction for this tool call.

        Read-only tools return a no-op action.
        Mutable tools (order, payment) return a real cancel/refund action.

        IMPORTANT: This is called by CompRegHook AFTER every successful run().
        Returning None breaks the post-hook chain.
        """
        raise NotImplementedError(f"Tool '{self.name}' must implement compensation()")

    async def ainvoke(
        self,
        input: str | dict[str, Any],
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Override ainvoke to return ToolResult instead of plain dict/str.

        LangChain's BaseTool.ainvoke returns the raw tool output.
        We wrap it in ToolResult for the SmartDay hook chain.
        """
        result = await super().ainvoke(input, config, **kwargs)
        if isinstance(result, ToolResult):
            return result
        # Wrap non-ToolResult outputs (e.g., from LangChain StructuredTool)
        return ToolResult(success=True, data={"result": result})

    def _idem_key(self, args: dict[str, Any]) -> str:
        """Generate a deterministic idempotency key from args (sha256).

        NEVER stores raw args — this hash is used as AuditEntry.args_hash too.
        """
        payload = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @staticmethod
    def _noop_compensation(action_id: str, tool_name: str) -> CompensationAction:
        """Return a no-op compensation for read-only tools (cache invalidation)."""

        async def _noop() -> None:
            pass

        return CompensationAction(
            action_id=action_id,
            tool_name=tool_name,
            description="No-op compensation (read-only tool)",
            execute=_noop,
        )
