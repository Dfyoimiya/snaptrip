"""LangGraph DAG 工作流 —— 分阶段流水线编排。

DAG 节点:
  extract → plan → execute
  每个节点内部是 LLM ReAct 子循环，通过条件边控制流转

Stage 1 (已实现): extract → LLM 提取意图/需求/约束
Stage 2-3 (待实现): plan → 搜索+求解, execute → 预订执行

Shared nodes:
  tools — 工具执行节点（阶段感知路由）
  hitl  — interrupt() 暂停等待用户交互

Author: SnapTrip Team
Date: 2026-05-31
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.agent_node import agent_node, route_after_agent
from agent.extract_node import extract_node
from agent.hitl_node import hitl_node
from agent.runtime import AgentRuntime
from agent.schemas.extract import ExtractResult
from agent.schemas.state import PlanState
from agent.tool_node import tool_node
from snaptrip_shared.core.config import settings

logger = logging.getLogger(__name__)

# ── 全局 DI ──
_runtime: AgentRuntime | None = None


# ── 条件路由函数 ────────────────────────────────────────────


def route_after_extract(state: PlanState) -> Literal["plan", "tools", "hitl"]:
    """extract 节点 → 下一节点路由。

    优先级:
    1. LLM 调用了 ask_user → "hitl" (暂停等用户回复)
    2. LLM 调用了 update_extract_result → "tools" (执行工具)
    3. LLM 输出纯文本:
       - extract_result 数据完备 → "plan" (进入规划阶段)
       - 数据不足 → "hitl" (触发 system prompt 中的澄清逻辑)
    """
    msgs = state.get("messages", [])
    if not msgs:
        return "hitl"

    last_msg = msgs[-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []

    if tool_calls:
        names = {tc["name"] if isinstance(tc, dict) else tc.name for tc in tool_calls}
        if "ask_user" in names:
            return "hitl"
        return "tools"

    # 纯文本：检查数据完备性
    extract_result: ExtractResult | None = state.get("extract_result")
    if extract_result is not None and extract_result.is_sufficient():
        logger.info("route_after_extract: extract complete → plan")
        return "plan"

    # 数据不足且 LLM 没有调用工具 — 注入 hitl_payload 触发澄清
    logger.info("route_after_extract: insufficient data → hitl (clarification)")
    return "hitl"


def route_after_tools(state: PlanState) -> Literal["extract", "plan"]:
    """tools 节点 → 返回的推理节点（阶段感知路由）。

    - extract 阶段 → 返回 extract_node (继续 ReAct 循环)
    - plan/execute 阶段 → 返回 plan_node (现有 agent_node)
    """
    phase = state.get("phase", "extract")
    if phase == "extract":
        return "extract"
    # 后续: phase == "plan" or "execute" → "plan" (agent_node)
    return "plan"


def route_after_hitl(state: PlanState) -> Literal["extract", "plan"]:
    """hitl 节点 → 用户回复后的下一节点（阶段感知路由）。"""
    phase = state.get("phase", "extract")
    if phase == "extract":
        return "extract"
    return "plan"


# ── 图构建 ─────────────────────────────────────────────────


async def build_graph(runtime: AgentRuntime | None = None) -> CompiledStateGraph:
    """构建 DAG 编排图。

    Nodes:
      extract — 意图提取 (LLM ReAct, EXTRACT_TOOLS)
      plan    — 搜索+求解 (现有 agent_node, ALL_TOOLS)
      tools   — 工具执行 (ToolHarness, 阶段感知路由)
      hitl    — 人机交互 (interrupt)

    Args:
        runtime: 依赖注入容器（可选）

    Returns:
        编译后的 CompiledStateGraph (使用 AsyncPostgresSaver)
    """
    global _runtime
    _runtime = runtime

    # ── 初始化 ToolHarness + SessionContext ──
    if runtime and runtime.harness is None:
        from agent.tools.bootstrap import build_registry
        from agent.tools.harness.context import SessionContext
        from agent.tools.harness.harness import ToolHarness

        runtime.harness = ToolHarness(registry=build_registry())
        runtime.session_ctx = SessionContext(
            amap_api_key=settings.AMAP_API_KEY,
        )
        logger.info(
            "ToolHarness initialized with %d tools",
            len(runtime.harness.registry.tool_names),
        )

    # ── 注入 AmapAdapter 单例 ──
    if runtime and runtime.tool_adapter:
        from agent.adapters.amap_adapter import set_default_adapter
        set_default_adapter(runtime.tool_adapter)
        logger.info("AmapAdapter injected via runtime.tool_adapter")
    elif runtime:
        from agent.adapters.amap_adapter import AmapAdapter, set_default_adapter
        set_default_adapter(AmapAdapter())
        logger.info("AmapAdapter created (no runtime.tool_adapter provided)")

    # ── 初始化 LLM adapter ──
    if runtime and runtime.llm_adapter is None:
        adapter_type = getattr(settings, "LLM_ADAPTER", "pydanticai")
        if adapter_type == "litellm":
            from agent.adapters.litellm_adapter import LiteLLMAdapter
            runtime.llm_adapter = LiteLLMAdapter()
            logger.info("LiteLLMAdapter initialized (LLM_ADAPTER=litellm)")
        else:
            from agent.adapters.pydanticai_adapter import PydanticAIAdapter
            runtime.llm_adapter = PydanticAIAdapter()
            logger.info("PydanticAIAdapter initialized (default)")

    # ── 构建 DAG ──
    graph = StateGraph(PlanState)

    # 注册节点
    graph.add_node("extract", extract_node)  # Step 1: 意图提取
    graph.add_node("plan", agent_node)       # Step 2: 规划 (现有 agent_node)
    graph.add_node("tools", tool_node)       # 工具执行 (共享)
    graph.add_node("hitl", hitl_node)        # 人机交互 (共享)

    graph.set_entry_point("extract")

    # ── E1: extract → tools / hitl / plan ──
    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {
            "tools": "tools",
            "hitl": "hitl",
            "plan": "plan",
        },
    )

    # ── E2: tools → extract / plan (阶段感知) ──
    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "extract": "extract",
            "plan": "plan",
        },
    )

    # ── E3: hitl → extract / plan (阶段感知) ──
    graph.add_conditional_edges(
        "hitl",
        route_after_hitl,
        {
            "extract": "extract",
            "plan": "plan",
        },
    )

    # ── E4: plan → tools / hitl / END (现有路由) ──
    graph.add_conditional_edges(
        "plan",
        route_after_agent,
        {
            "tools": "tools",
            "hitl": "hitl",
            "end": END,
        },
    )

    # ── Checkpointer ──
    db_url = settings.DATABASE_URL
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
        await checkpointer.setup()
        logger.info("PostgresSaver initialized for graph checkpointing")
    except Exception:
        logger.warning(
            "PostgresSaver setup failed, falling back to MemorySaver. "
            "Checkpoint state will be lost on restart."
        )
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
