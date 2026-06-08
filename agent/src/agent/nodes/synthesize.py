"""Synthesize — compose final response from specialist results."""

from __future__ import annotations

import logging
from typing import Any

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

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


# ── Node ─────────────────────────────────────────────────────────────────────


async def synthesize_node(state: PlanState) -> dict:
    """Synthesize final response from specialist results.

    Reviews the full conversation (user messages, AI tool calls, tool results)
    and produces a polished final response. Also stores the specialist agent's
    contribution in sub_results.

    Returns:
        dict with final AIMessage and status="done"
    """
    from agent.graph import _runtime

    adapter = _runtime.llm_adapter if _runtime else None
    if not adapter:
        logger.error("synthesize: LLM adapter unavailable")
        # Fallback: return last assistant message as final
        messages = state.get("messages", [])
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if content and getattr(msg, "type", None) == "ai":
                return {"phase": "done", "status": "done"}

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

    try:
        response = await adapter.chat(
            messages=llm_messages,
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("synthesize: LLM call failed")
        return {"phase": "done", "status": "done", "sub_results": sub_results}

    return {
        "messages": [response],
        "phase": "done",
        "status": "done",
        "sub_results": sub_results,
    }
