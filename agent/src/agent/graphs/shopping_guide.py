# ────────────────────────────────────────────────────────────────────────────
# 🔵 Shopping Guide Agent — Independent LangGraph DAG
# ────────────────────────────────────────────────────────────────────────────
# Standalone graph for the C-end shopping guide. Does NOT go through the
# main supervisor-specialist routing. All tools are read-only.
#
# Topology:
#   START → shopping_guide → route_after_specialist:
#     ├─ tools → back to shopping_guide (loop)
#     └─ synthesize → END
# ────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.nodes.shopping_guide import shopping_guide_node
from agent.runtime import AgentRuntime
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)
_trace_logger = logging.getLogger("agent.trace")

# ── Global DI ──
_shopping_runtime: AgentRuntime | None = None

SHOPPING_SPECIALIST = "shopping_guide"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_harness_and_session():
    """Get ToolHarness + SessionContext from shopping guide runtime."""
    if _shopping_runtime:
        return _shopping_runtime.harness, _shopping_runtime.session_ctx
    return None, None


def _parse_tool_call(tc: dict | Any) -> tuple[str, str, dict[str, Any]]:
    """Normalize a LangChain tool call into (id, name, args dict)."""
    tc_id = tc["id"] if isinstance(tc, dict) else tc.id
    tc_name = tc["name"] if isinstance(tc, dict) else tc.name
    if isinstance(tc, dict):
        raw_args = tc.get("args", tc.get("arguments", {}))
        tc_args: dict[str, Any] = (
            json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        )
    else:
        raw_args = getattr(tc, "args", getattr(tc, "arguments", {}))
        tc_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    return tc_id, tc_name, tc_args


# ── Tool dispatch node (simplified — no Saga, no HITL) ───────────────────────


async def shopping_tool_node(state: PlanState) -> dict:
    """Execute read-only shopping guide tool calls via ToolHarness.

    All shopping tools are standard (non-saga, non-user-facing), so the
    dispatch is a simple loop over tool_calls → harness.execute().

    Returns:
        {"messages": [ToolMessage(...)], "phase": "shopping_tools"}
    """
    harness, session_ctx = _get_harness_and_session()

    if session_ctx and state.get("user_id"):
        session_ctx.user_id = state["user_id"]

    # JWT passthrough
    auth_token = state.get("working_memory", {}).get("auth_token", "")
    if auth_token and session_ctx:
        session_ctx.metadata["auth_token"] = auth_token
        from agent.tools.auth import set_auth_token
        set_auth_token(auth_token)
    else:
        from agent.tools.auth import set_auth_token
        set_auth_token("")

    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []

    results: list[ToolMessage] = []

    for tc in tool_calls:
        tc_id, tc_name, tc_args = _parse_tool_call(tc)
        logger.debug("shopping_tool_node: executing %s", tc_name)

        if harness and session_ctx:
            try:
                result = await harness.execute(
                    tool_name=tc_name,
                    args=tc_args,
                    session_ctx=session_ctx,
                )
                data = (
                    result.data
                    if result.success
                    else {"error": result.data.get("error", "unknown")}
                )
            except Exception as e:
                logger.exception("ToolHarness execution failed for %s", tc_name)
                data = {"error": f"{type(e).__name__}: {e}"}
        else:
            data = {"error": "ToolHarness not available"}

        results.append(
            ToolMessage(
                content=json.dumps(data, ensure_ascii=False),
                tool_call_id=tc_id,
            )
        )

    return {"messages": results, "phase": "shopping_tools"}


# ── Synthesize node ──────────────────────────────────────────────────────────


SHOPPING_SYNTHESIZE_PROMPT = """You are a response synthesizer for SnapTrip, an e-commerce platform.

Your job is to review the conversation history from the shopping guide and produce a clean,
well-structured final response for the user.

Guidelines:
1. Read through ALL messages to understand the full conversation flow.
2. Extract key product information and present it clearly.
3. For EVERY product mentioned, include a clickable purchase link:
   [View {product_name}](/product/{product_id})
4. Format the response in a user-friendly way:
   - Use clear sections for different products or categories
   - Highlight prices, discounts, and key features
   - If comparing products, use a structured table format
5. Include a helpful next step or call-to-action when appropriate.
6. If there were errors or no results, acknowledge this honestly and suggest alternatives.
7. NEVER add product information that does not appear in the conversation history.

Respond in the user's language. Be enthusiastic but honest."""


async def shopping_synthesize_node(state: PlanState) -> dict:
    """Synthesize final response from shopping guide results.

    Returns:
        dict with final AIMessage, phase="done", status="done"
    """
    t0 = time.monotonic()

    harness, _ = _get_harness_and_session()
    adapter = _shopping_runtime.llm_adapter if _shopping_runtime else None

    if not adapter:
        logger.error("shopping_synthesize: LLM adapter unavailable")
        return {"phase": "done", "status": "done"}

    messages = state.get("messages", [])

    # Build conversation for synthesis
    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": SHOPPING_SYNTHESIZE_PROMPT},
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
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("shopping_synthesize: LLM call failed")
        elapsed = (time.monotonic() - t0) * 1000
        _trace_logger.error(
            "node_trace name=shopping_synthesize elapsed_ms=%.1f success=false error=llm_error",
            elapsed,
        )
        return {"phase": "done", "status": "done"}

    elapsed = (time.monotonic() - t0) * 1000
    _trace_logger.info(
        "node_trace name=shopping_synthesize elapsed_ms=%.1f success=true status=done",
        elapsed,
    )
    return {
        "messages": [response],
        "phase": "done",
        "status": "done",
    }


# ── Conditional routing ──────────────────────────────────────────────────────


def route_after_shopping_guide(state: PlanState) -> Literal["shopping_tools", "shopping_synthesize"]:
    """After shopping guide node: if tool_calls exist -> tools, else -> synthesize."""
    msgs = state.get("messages", [])
    if not msgs:
        return "shopping_synthesize"
    last_msg = msgs[-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    return "shopping_tools" if tool_calls else "shopping_synthesize"


def route_after_shopping_tools(state: PlanState) -> Literal["shopping_guide"]:
    """After tool execution: always return to the shopping guide specialist."""
    return "shopping_guide"


# ── Graph builder ────────────────────────────────────────────────────────────


async def build_shopping_guide_graph(
    runtime: AgentRuntime | None = None,
) -> CompiledStateGraph:
    """Build the standalone shopping guide agent DAG.

    Topology:
      START → shopping_guide → route_after_shopping_guide:
        ├─ shopping_tools → shopping_guide (loop)
        └─ shopping_synthesize → END

    Args:
        runtime: optional DI container (AgentRuntime)

    Returns:
        CompiledStateGraph with MemorySaver checkpointer
    """
    global _shopping_runtime
    _shopping_runtime = runtime

    # ── Initialize ToolHarness with shopping guide tools ──
    if runtime and runtime.harness is None:
        from agent.tools.harness.context import SessionContext
        from agent.tools.harness.harness import ToolHarness
        from agent.tools.bootstrap_shopping import build_shopping_guide_registry

        runtime.harness = ToolHarness(registry=build_shopping_guide_registry())
        runtime.session_ctx = SessionContext()
        logger.info(
            "Shopping Guide ToolHarness initialized with %d tools",
            len(runtime.harness.registry.tool_names),
        )

    # ── Initialize LLM adapter ──
    if runtime and runtime.llm_adapter is None:
        from agent.utils import get_llm_adapter
        runtime.llm_adapter = get_llm_adapter()
        logger.info("Shopping Guide LLM adapter initialized")

    # ── Build DAG ──
    graph = StateGraph(PlanState)

    graph.add_node("shopping_guide", shopping_guide_node)
    graph.add_node("shopping_tools", shopping_tool_node)
    graph.add_node("shopping_synthesize", shopping_synthesize_node)

    graph.set_entry_point("shopping_guide")

    # Specialist → tools or synthesize
    graph.add_conditional_edges(
        "shopping_guide",
        route_after_shopping_guide,
        {
            "shopping_tools": "shopping_tools",
            "shopping_synthesize": "shopping_synthesize",
        },
    )

    # Tools → back to specialist
    graph.add_conditional_edges(
        "shopping_tools",
        route_after_shopping_tools,
        {"shopping_guide": "shopping_guide"},
    )

    # Synthesize → END
    graph.add_edge("shopping_synthesize", END)

    return graph.compile(checkpointer=MemorySaver())
