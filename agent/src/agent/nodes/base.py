"""BaseSpecialist — Template Method base for specialist agent nodes.

Eliminates the ~45 lines of copy-pasted boilerplate across all specialist nodes.
Derived from the reference multi-agent-ecommerce-system BaseAgent pattern.

Subclasses set: node_name, system_prompt, tools, phase_name, temperature.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# Shared trace logger for all BaseSpecialist instances
_trace_logger = logging.getLogger("agent.trace")


class BaseSpecialist:
    """Template method base for all specialist LangGraph nodes.

    Subclasses override class-level constants to define their behavior.
    The module-level async function delegates to `.execute()` for graph compatibility.
    """

    # ── Subclass overrides ──────────────────────────────────────────────────

    node_name: str = ""
    system_prompt: str = ""
    tools: list[dict[str, Any]] = []
    phase_name: str = ""
    temperature: float = 0.3
    max_retries: int = 3
    retry_base_delay: float = 1.0  # seconds, doubles each retry: 1s, 2s, 4s
    max_tokens: int = 2048

    # ── Template method ─────────────────────────────────────────────────────

    async def execute(self, state: PlanState) -> dict:
        """Template method: adapter check → retry guard → build messages → LLM call.

        Returns a state update dict with messages, phase, current_agent, retry_count.
        """
        t0 = time.monotonic()

        from agent.graph import _runtime

        adapter = _runtime.llm_adapter if _runtime else None
        if not adapter:
            elapsed = (time.monotonic() - t0) * 1000
            _trace_logger.error(
                "node_trace name=%s elapsed_ms=%.1f success=false error=no_adapter",
                self.node_name,
                elapsed,
            )
            return {"phase": "error", "status": "llm_unavailable"}

        retry_count = state.get("retry_count", 0)
        if retry_count >= self.max_retries:
            elapsed = (time.monotonic() - t0) * 1000
            _trace_logger.info(
                "node_trace name=%s elapsed_ms=%.1f success=true status=max_retries",
                self.node_name,
                elapsed,
            )
            return {"phase": self.phase_name, "status": "max_retries"}

        llm_messages = self._build_messages(state)

        try:
            response = await self._call_with_backoff(adapter, llm_messages, retry_count)
        except Exception:
            elapsed = (time.monotonic() - t0) * 1000
            _trace_logger.error(
                "node_trace name=%s elapsed_ms=%.1f success=false error=llm_error",
                self.node_name,
                elapsed,
            )
            return {"phase": "error", "status": "llm_error"}

        elapsed = (time.monotonic() - t0) * 1000
        _trace_logger.info(
            "node_trace name=%s elapsed_ms=%.1f success=true status=ok",
            self.node_name,
            elapsed,
        )
        return {
            "messages": [response],
            "phase": self.phase_name,
            "current_agent": self.node_name,
            "retry_count": retry_count + 1,
        }

    # ── Message conversion ──────────────────────────────────────────────────

    def _build_messages(self, state: PlanState) -> list[dict[str, Any]]:
        """Convert LangChain message history to OpenAI dict format.

        Handles role mapping (human→user, ai→assistant, tool→tool),
        tool_calls normalization, and tool_call_id propagation.
        """
        messages = state.get("messages", [])
        llm_messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
        ]
        for msg in messages:
            if hasattr(msg, "type"):
                role = msg.type
                content = msg.content or ""
                role_map = {"human": "user", "ai": "assistant", "tool": "tool"}
                api_role = role_map.get(role, role)
                entry: dict[str, Any] = {"role": api_role, "content": content}
                if role == "ai":
                    tcs = getattr(msg, "tool_calls", None) or []
                    if tcs:
                        from agent.utils import normalize_tool_calls_for_api

                        entry["tool_calls"] = normalize_tool_calls_for_api(tcs)
                if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                    entry["tool_call_id"] = msg.tool_call_id
                llm_messages.append(entry)
            elif isinstance(msg, dict):
                llm_messages.append(msg)
        return llm_messages

    # ── Retry with backoff ──────────────────────────────────────────────────

    async def _call_with_backoff(
        self, adapter: Any, messages: list[dict[str, Any]], attempt: int
    ) -> Any:
        """Call LLM with exponential backoff on failure.

        Retry schedule: attempt 0 → try 3 times (1s, 2s, 4s delays)
                       attempt 1 → try 2 times (1s, 2s delays)
                       attempt 2 → try 1 time  (no retry)
        """
        remaining = self.max_retries - attempt
        last_exc: Exception | None = None

        for i in range(remaining):
            try:
                return await adapter.chat(
                    messages=messages,
                    tools=self.tools,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as exc:
                last_exc = exc
                if i < remaining - 1:
                    delay = self.retry_base_delay * (2**i)
                    logger.warning(
                        "%s: LLM attempt %d failed, retrying in %.1fs",
                        self.node_name,
                        attempt + i + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)

        raise last_exc  # type: ignore[misc]
