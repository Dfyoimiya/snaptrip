"""Synthesize — compose final response from specialist results."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, cast

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)
_trace_logger = logging.getLogger("agent.trace")

# ── System prompt for synthesis ──────────────────────────────────────────────

SYNTHESIZE_SYSTEM_PROMPT = """You are a response synthesizer for SnapTrip, a travel e-commerce platform.

Your job is to review the conversation history and produce a clean, well-structured final response
for the user. The conversation history includes the user's original query, tool calls made by
specialist agents, and tool results.

Guidelines:
1. Read through ALL messages to understand the full conversation flow.
2. Extract the key information from tool results and present it clearly.
3. If the user asked a question, make sure the answer is complete and accurate.
4. Format the response in a user-friendly way:
   - Use clear sections for different pieces of information
   - Highlight key details like prices, dates, and action items
   - If presenting multiple options, number them
5. Include a helpful next step or call-to-action when appropriate.
6. If there were errors or no results, acknowledge this honestly and suggest alternatives.
7. NEVER add information that does not appear in the conversation history.

Respond in the user's language. Be concise but thorough.
"""


# ── Response helpers ─────────────────────────────────────────────────────────


def _extract_json_content(text: str) -> str:
    """Extract clean answer text from JSON-structured response.

    If the text is valid JSON with 'answer'/'highlights' fields,
    returns a markdown-formatted version. Otherwise returns original text.
    """
    if not text:
        return text

    # Try to find JSON object in the text (strip markdown code blocks)
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "answer" in data:
            parts = [data["answer"]]
            highlights = data.get("highlights", [])
            if highlights:
                parts.append("\n**要点:**")
                for h in highlights:
                    parts.append(f"- {h}")
            return "\n".join(parts)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to find JSON anywhere in text
    match = re.search(r'\{[^{}]*"answer"\s*:\s*"[^"]+"[^{}]*\}', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, dict) and "answer" in data:
                return cast(str, data["answer"])
        except (json.JSONDecodeError, TypeError):
            pass

    return text


# ── Node ─────────────────────────────────────────────────────────────────────


async def synthesize_node(state: PlanState) -> dict:
    """Synthesize final response from specialist results.

    Reviews the full conversation (user messages, AI tool calls, tool results)
    and produces a polished final response. Also stores the specialist agent's
    contribution in sub_results.

    Returns:
        dict with final AIMessage and status="done"
    """
    t0 = time.monotonic()
    from agent.graph import _runtime

    adapter = _runtime.llm_adapter if _runtime else None
    if not adapter:
        logger.error("synthesize: LLM adapter unavailable")
        messages = state.get("messages", [])
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if content and getattr(msg, "type", None) == "ai":
                return {"phase": "done", "status": "done", "messages": messages}

    messages = state.get("messages", [])

    # Build conversation for synthesis
    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYNTHESIZE_SYSTEM_PROMPT},
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

    # Store specialist contribution in sub_results
    current_agent = state.get("current_agent", "unknown")
    sub_results = dict(state.get("sub_results", {}))
    sub_results[current_agent] = {
        "phase": state.get("phase", ""),
        "message_count": len(messages),
    }

    if adapter is None:
        logger.error("synthesize: no LLM adapter available")
        return {
            "phase": "done",
            "status": "done",
            "sub_results": sub_results,
            "messages": messages,
        }

    try:
        response = await adapter.chat(
            messages=llm_messages,
            temperature=0.3,
            max_tokens=2048,
        )
        # Extract structured JSON content for cleaner display
        raw_content = (
            response.content if hasattr(response, "content") else str(response)
        )
        cleaned = _extract_json_content(str(raw_content))
        if cleaned != raw_content:
            if hasattr(response, "content"):
                response.content = cleaned
    except Exception:
        logger.exception("synthesize: LLM call failed")
        elapsed = (time.monotonic() - t0) * 1000
        _trace_logger.error(
            "node_trace name=synthesize elapsed_ms=%.1f success=false error=llm_error",
            elapsed,
        )
        return {
            "phase": "done",
            "status": "done",
            "sub_results": sub_results,
            "messages": messages,
        }

    elapsed = (time.monotonic() - t0) * 1000
    _trace_logger.info(
        "node_trace name=synthesize elapsed_ms=%.1f success=true status=done",
        elapsed,
    )
    return {
        "messages": [response],
        "phase": "done",
        "status": "done",
        "sub_results": sub_results,
    }
