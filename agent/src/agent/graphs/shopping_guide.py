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


SHOPPING_SYNTHESIZE_PROMPT = """你是一个回复润色专家，为电商平台 SnapTrip 服务。请始终用中文回复。

你的工作是审核导购对话中的完整历史记录，为用户生成简洁、结构清晰的最终回复。

## 准则
1. 通读所有消息，理解完整对话流程。
2. 提取对话中出现的所有商品信息（工具返回结果、之前的回复）。
3. 润色回复文字：简洁、有条理、易于阅读。
4. 为每件提到的商品在回复中附带购买链接：
   [查看 {商品名称}](/product/{商品ID})
5. 突出价格、折扣和关键特色。
6. 如果有错误或没有结果，坦诚告知并建议替代方案。
7. 绝不编造商品信息——仅包含对话中实际出现的商品。

## 输出格式
必须输出包含以下字段的 JSON 对象：

```json
{
  "answer": "润色后的完整导购建议，内嵌商品购买链接。",
  "products": [
    {
      "name": "商品名称",
      "price": 99.00,
      "original_price": 129.00,
      "discount": "7.7折",
      "link": "/product/abc123",
      "highlights": ["亮点1", "亮点2"]
    }
  ],
  "follow_up_questions": [
    "自然的追问 1",
    "自然的追问 2"
  ]
}
```

重要：
- 将对话中出现的所有商品放入 products 数组（使用工具返回结果中的准确数据）。
- 包含 2-3 条上下文相关、自然的追问。
- answer 字段是润色后的导购建议，内嵌商品链接。
- 如果没有商品，将 products 设为空数组 []。

只输出 JSON 对象，不要用 markdown 代码围栏，不要多余文字。"""


async def shopping_synthesize_node(state: PlanState) -> dict:
    """Synthesize final response from shopping guide results.

    If _stream_callback is set in working_memory, streams tokens via the callback.
    Otherwise falls back to a single adapter.chat() call.

    Returns:
        dict with final AIMessage, phase="done", status="done"
    """
    from langchain_core.messages import AIMessage as LangAIMessage

    t0 = time.monotonic()

    harness, _ = _get_harness_and_session()
    adapter = _shopping_runtime.llm_adapter if _shopping_runtime else None

    if not adapter:
        logger.error("shopping_synthesize: LLM adapter unavailable")
        return {"phase": "done", "status": "done"}

    messages = state.get("messages", [])
    stream_callback = state.get("working_memory", {}).get("_stream_callback")

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
        if stream_callback and hasattr(adapter, "chat_stream"):
            # ── 流式模式 ──
            collected = ""
            async for token in adapter.chat_stream(
                messages=llm_messages,
                temperature=0.3,
                max_tokens=2048,
            ):
                collected += token
                try:
                    await stream_callback(token)
                except Exception:
                    pass  # 客户端断开，继续收集但不推送

            response = LangAIMessage(content=collected)
        else:
            # ── 非流式模式 ──
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
