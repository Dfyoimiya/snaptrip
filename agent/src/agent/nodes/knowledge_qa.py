"""Knowledge QA — FAQ, general questions, store policies."""

from __future__ import annotations

import logging
from typing import Any

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── Tool definitions ─────────────────────────────────────────────────────────

KNOWLEDGE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the SnapTrip knowledge base for FAQs, policies, "
                           "and general information. Covers payment methods, account management, "
                           "store locations, cancellation policies, insurance, visa requirements, "
                           "and general travel tips.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query for the knowledge base",
                    },
                    "topic": {
                        "type": "string",
                        "enum": [
                            "payment", "account", "cancellation", "insurance",
                            "visa", "store", "general", "all",
                        ],
                        "description": "Topic filter to narrow results (default: 'all')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 3, max: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# ── System prompt ────────────────────────────────────────────────────────────

KNOWLEDGE_SYSTEM_PROMPT = """You are a knowledgeable customer service agent for SnapTrip, a travel e-commerce platform.

Your job is to answer general questions about SnapTrip's services, policies, and travel-related topics.

Guidelines:
1. Use 'search_knowledge' to look up answers in the knowledge base. Always search
   before answering factual questions — do not guess or fabricate information.
2. If the knowledge base returns relevant information, summarize it clearly for the user.
3. If the question is beyond what the knowledge base covers, be honest and suggest
   contacting human support or visiting the website for more details.
4. Common topics include: payment methods, account registration, cancellation policies,
   insurance options, visa requirements, store locations, and general travel tips.
5. Be polite, concise, and helpful.
6. NEVER call a tool that you don't have defined.

Respond in the user's language.
"""


# ── Node ─────────────────────────────────────────────────────────────────────


async def knowledge_qa_node(state: PlanState) -> dict:
    """Answer general questions. Calls search_knowledge tool.

    Returns:
        dict with updated messages and phase. AIMessage may contain tool_calls
        which the graph routes to tool_node.
    """
    from agent.graph import _runtime

    adapter = _runtime.llm_adapter if _runtime else None
    if not adapter:
        logger.error("knowledge_qa: LLM adapter unavailable")
        return {"phase": "error", "status": "llm_unavailable"}

    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)

    if retry_count > 3:
        logger.warning("knowledge_qa: max retries exceeded, forcing synthesize")
        return {"phase": "knowledge_qa", "status": "max_retries"}

    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": KNOWLEDGE_SYSTEM_PROMPT},
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

    try:
        response = await adapter.chat(
            messages=llm_messages,
            tools=KNOWLEDGE_TOOLS,
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("knowledge_qa: LLM call failed")
        return {"phase": "error", "status": "llm_error"}

    return {
        "messages": [response],
        "phase": "knowledge_qa",
        "current_agent": "knowledge_qa",
        "retry_count": retry_count + 1,
    }
