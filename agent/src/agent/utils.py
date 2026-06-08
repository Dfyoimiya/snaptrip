# ────────────────────────────────────────────────────────────────────────────
# 🔵 FRAMEWORK — Shared Utilities
# ────────────────────────────────────────────────────────────────────────────
# Common functions shared across nodes and adapters.
#
# Trip-specific constants (INTERNAL_NAMES, trip tool sets) have been removed.
# Define your own tool name sets below.
#
# Archived: 2026-06-07 — repurposed from trip planning agent
# ────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
from typing import Any

from agent.ports.llm import LLMPort

logger = logging.getLogger(__name__)

# ── Tool name sets — customize for your domain ─────────────────────────────

# Tool names that trigger HITL interrupt (don't execute, set hitl_payload)
USER_FACING_NAMES: set[str] = set()

# Tool names that execute via SagaCoordinator (reserve → confirm → rollback)
EXECUTION_NAMES: set[str] = {"cancel_order"}


# ── Message utilities ──────────────────────────────────────────────────────


def strip_orphan_tool_calls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip orphan tool_calls that have no corresponding ToolMessage.

    When the LLM calls both user-facing and non-user-facing tools, but routing
    sends to hitl (user-facing takes priority), non-user-facing tool_calls are
    never executed — resulting in tool_calls without ToolMessage, which the API
    rejects.
    """
    responded_ids: set[str] = set()
    for m in messages:
        if m.get("role") == "tool":
            tc_id = m.get("tool_call_id", "")
            if tc_id:
                responded_ids.add(tc_id)

    for m in messages:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            tcs = m["tool_calls"]
            valid = [tc for tc in tcs if tc.get("id", "") in responded_ids]
            if len(valid) == len(tcs):
                continue
            if valid:
                m["tool_calls"] = valid
            else:
                del m["tool_calls"]
                m.pop("reasoning_content", None)

    return messages


def normalize_tool_calls_for_api(tool_calls: list[Any]) -> list[dict[str, Any]]:
    """Convert LangChain ToolCall format to OpenAI API format.

    LangChain: {"name": ..., "args": {...}, "id": ..., "type": "tool_call"}
    OpenAI:    {"id": ..., "type": "function", "function": {"name": ..., "arguments": ...}}
    """
    result: list[dict[str, Any]] = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            if "function" in tc:
                result.append(tc)
            else:
                name = tc.get("name", "")
                args = tc.get("args", {})
                result.append(
                    {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args, ensure_ascii=False)
                            if not isinstance(args, str)
                            else args,
                        },
                    }
                )
        else:
            name = getattr(tc, "name", "")
            args = getattr(tc, "args", {})
            result.append(
                {
                    "id": getattr(tc, "id", ""),
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(args, ensure_ascii=False)
                        if not isinstance(args, str)
                        else args,
                    },
                }
            )
    return result


def safe_parse_json(raw: str) -> dict[str, Any]:
    """Safely parse JSON that may contain extra content beyond the JSON object.

    LLMs sometimes return {...}{...} or {...}extra text in tool-call arguments.
    Extracts the outermost complete JSON object.
    """
    raw = raw.strip()
    if not raw.startswith("{"):
        return {}
    depth = 0
    end = 0
    for i, ch in enumerate(raw):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == 0:
        return {}
    try:
        return json.loads(raw[:end])
    except json.JSONDecodeError:
        return {}


def strip_none_values(o: Any) -> Any:
    """Recursively strip None values from dicts/lists.

    Allows Pydantic models to use their own field defaults
    instead of explicit None values from the LLM.
    """
    if isinstance(o, dict):
        return {k: strip_none_values(v) for k, v in o.items() if v is not None}
    if isinstance(o, list):
        return [strip_none_values(v) for v in o]
    return o


# ── Infrastructure utilities ───────────────────────────────────────────────


def get_event_bus():
    """Get the Runtime event_bus (may be None)."""
    from agent.graph import _runtime

    if _runtime:
        return _runtime.event_bus
    return None


def get_llm_adapter() -> LLMPort:
    """Resolve the LLM adapter from runtime or settings."""
    from agent.graph import _runtime

    if _runtime and _runtime.llm_adapter:
        return _runtime.llm_adapter

    from agent.adapters.langchain_adapter import LangChainAdapter

    return LangChainAdapter()
