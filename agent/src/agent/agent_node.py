"""Agent Node —— LLM ReAct 推理主节点。

LLM 持有全部工具，自主推理并决定下一步：
- 调用搜索工具获取 POI
- 调用求解器优化行程
- 调用 ask_user 发起澄清/协商
- 调用 present_plan 展示方案
- 调用预订工具执行
- 输出最终消息结束

Author: SnapTrip Team
Date: 2026-05-29
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel

from agent.prompts.system import AGENT_SYSTEM_PROMPT
from agent.schemas.extract import UpdateExtractResultInput
from agent.schemas.state import PlanState
from agent.schemas.tool_inputs import (
    INTERNAL_TOOL_DEFS,
    USER_FACING_TOOL_DEFS,
    AskUserInput,
    PresentBookingInput,
    PresentPlanInput,
    UpdateItineraryInput,
)
from snaptrip_shared.core.config import settings

logger = logging.getLogger(__name__)

# ── Tool arg Pydantic models for runtime validation ──
_TOOL_ARG_MODELS: dict[str, type[BaseModel]] = {
    "update_extract_result": UpdateExtractResultInput,
    "ask_user": AskUserInput,
    "present_plan": PresentPlanInput,
    "present_booking": PresentBookingInput,
    "update_itinerary": UpdateItineraryInput,
}


def _build_all_tool_defs(harness_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """合并所有工具定义: Harness 工具 + user-facing + internal state。"""
    return list(harness_tools) + USER_FACING_TOOL_DEFS + INTERNAL_TOOL_DEFS


def _normalize_tool_calls_for_api(tool_calls: list[Any]) -> list[dict[str, Any]]:
    """将 LangChain ToolCall 转换为 OpenAI API 格式。

    LangChain 格式: {"name": ..., "args": {...}, "id": ..., "type": "tool_call"}
    OpenAI/DeepSeek 格式: {"id": ..., "type": "function", "function": {"name": ..., "arguments": ...}}
    """
    result: list[dict[str, Any]] = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            if "function" in tc:
                result.append(tc)  # already in OpenAI format
            else:
                name = tc.get("name", "")
                args = tc.get("args", {})
                result.append({
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args,
                    },
                })
        else:
            name = getattr(tc, "name", "")
            args = getattr(tc, "args", {})
            result.append({
                "id": getattr(tc, "id", ""),
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args,
                },
            })
    return result


def _build_messages(state: PlanState) -> list[dict[str, Any]]:
    """从 PlanState 构建 LLM 消息列表。"""
    msgs: list[dict[str, Any]] = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]

    # 添加用户位置信息
    lat = state.get("lat")
    lng = state.get("lng")
    if lat is not None and lng is not None:
        lat_lng_msg = f"用户当前位置: lat={lat}, lng={lng}。可以使用 amap_geocode 工具反向地理编码获取具体城市/区域。在给用户推荐或搜索地点时，应当优先考虑用户所在位置附近。"

        # 第一轮对话且位置已知：强制要求先搜索再提问
        msg_count = len(state.get("messages", []))
        if msg_count <= 2:
            lat_lng_msg += "\n\n⚠️ 这是对话的第一轮。你必须立即调用 amap_geocode(location=\"lng,lat\") 和 amap_poi_search 了解用户周边环境。在完成搜索之前，禁止调用 ask_user。"

        msgs.append({
            "role": "system",
            "content": lat_lng_msg,
        })

    # 添加已有的结构化信息作为上下文（使用新的 ExtractResult）
    extract_result = state.get("extract_result")
    if extract_result is not None:
        existing = extract_result.model_dump(exclude_none=True)
        msgs.append({
            "role": "system",
            "content": f"当前已提取的用户意图: {json.dumps(existing, ensure_ascii=False)}",
        })

    profile = state.get("user_profile")
    if profile and any(v for v in profile.values() if v):
        msgs.append({
            "role": "system",
            "content": f"当前用户画像: {json.dumps(profile, ensure_ascii=False)}",
        })

    candidates = state.get("activity_candidates", [])
    if candidates:
        msgs.append({
            "role": "system",
            "content": f"已搜索到的活动候选 ({len(candidates)} 个): {json.dumps(candidates[:5], ensure_ascii=False)}",
        })

    rst_candidates = state.get("restaurant_candidates", [])
    if rst_candidates:
        msgs.append({
            "role": "system",
            "content": f"已搜索到的餐厅候选 ({len(rst_candidates)} 个): {json.dumps(rst_candidates[:5], ensure_ascii=False)}",
        })

    pareto = state.get("pareto_solutions")
    if pareto:
        msgs.append({
            "role": "system",
            "content": f"Pareto 前沿解集 ({len(pareto)} 个): {json.dumps(pareto, ensure_ascii=False)}",
        })

    # 添加对话历史
    for m in state.get("messages", []):
        if isinstance(m, SystemMessage):
            msgs.append({"role": "system", "content": str(m.content)})
        elif isinstance(m, HumanMessage):
            msgs.append({"role": "user", "content": str(m.content)})
        elif isinstance(m, AIMessage):
            msg: dict[str, Any] = {"role": "assistant", "content": str(m.content) if m.content else None}
            if hasattr(m, "tool_calls") and m.tool_calls:
                msg["tool_calls"] = _normalize_tool_calls_for_api(m.tool_calls)
                # DeepSeek 要求：有 tool_calls 的轮次需回传 reasoning_content
                rc = getattr(m, "reasoning_content", None)
                if rc:
                    msg["reasoning_content"] = rc
            msgs.append(msg)
        elif isinstance(m, ToolMessage):
            msgs.append({
                "role": "tool",
                "tool_call_id": getattr(m, "tool_call_id", ""),
                "content": str(m.content),
            })

    return msgs


def _safe_parse_json(raw: str) -> dict[str, Any]:
    """安全解析 LLM 返回的可能含多余内容的 JSON。

    LLM 有时会在 tool-call arguments 里返回 `{...}{...}` 或
    `{...}extra text` 等格式。尝试提取最外层完整 JSON 对象。
    """
    raw = raw.strip()
    # 找到第一个 { 和对应的 }
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


def _validate_tool_args(name: str, raw_args: str | dict) -> dict[str, Any]:
    """Parse and validate LLM tool-call arguments against Pydantic model.

    Returns validated & default-filled args dict. On failure, returns the
    best-effort parsed args so the tool_node can still attempt execution
    and return an error ToolMessage to the LLM.
    """
    model = _TOOL_ARG_MODELS.get(name)
    if model is None:
        if isinstance(raw_args, str):
            try:
                return json.loads(raw_args)
            except json.JSONDecodeError:
                return {}
        return raw_args if isinstance(raw_args, dict) else {}

    # Parse JSON string → dict
    if isinstance(raw_args, str):
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            logger.warning(
                "agent_node: malformed JSON in tool %s args, trying recovery", name,
            )
            recovered = _safe_parse_json(raw_args)
            if not recovered:
                logger.error(
                    "agent_node: unrecoverable JSON for tool %s: %s",
                    name, raw_args[:200],
                )
                return {}
            args = recovered
    else:
        args = raw_args

    # Pydantic validation: fill defaults, check types
    try:
        validated = model.model_validate(args)
        return validated.model_dump()
    except Exception:
        logger.warning(
            "agent_node: Pydantic validation for %s failed, using raw args. "
            "Args: %s", name, str(args)[:200],
            exc_info=True,
        )
        return args


async def agent_node(state: PlanState) -> dict:
    """LLM ReAct 主节点。

    1. 从 state 构建消息列表（system prompt + 结构化信息 + 对话历史）
    2. 合并所有可用工具（Harness 工具 + user-facing + internal state）
    3. 调用 LLM
    4. 返回 LLM 响应（含 tool_calls 或 final message）
    """
    from agent.graph import _runtime

    # 获取 LLM adapter
    if _runtime and _runtime.llm_adapter:
        llm = _runtime.llm_adapter
    else:
        adapter_type = getattr(settings, "LLM_ADAPTER", "pydanticai")
        if adapter_type == "litellm":
            from agent.adapters.litellm_adapter import LiteLLMAdapter
            llm = LiteLLMAdapter()
        else:
            from agent.adapters.pydanticai_adapter import PydanticAIAdapter
            llm = PydanticAIAdapter()

    # 获取 ToolHarness 工具列表
    harness_tools: list[dict[str, Any]] = []
    if _runtime and _runtime.harness:
        strict_mode = getattr(settings, "LLM_STRICT_MODE", False)
        harness_tools = _runtime.harness.list_tools(strict=strict_mode)

    messages = _build_messages(state)
    all_tools = _build_all_tool_defs(harness_tools)

    logger.info(
        "agent_node: %d messages, %d tools (%d harness + %d user-facing + %d internal)",
        len(messages), len(all_tools),
        len(harness_tools), len(USER_FACING_TOOL_DEFS), len(INTERNAL_TOOL_DEFS),
    )

    response = await llm.chat(
        messages=messages,
        tools=all_tools,
        temperature=0.3,
        max_tokens=2048,
        timeout_s=120,
    )

    # 构造 AIMessage
    ai_kwargs: dict[str, Any] = {}
    if response.get("content"):
        ai_kwargs["content"] = response["content"]
    rc = response.get("reasoning_content")
    if rc:
        ai_kwargs["reasoning_content"] = rc
    if response.get("tool_calls"):
        # Normalize tool_calls: OpenAI format → langchain_core format
        normalized: list[dict[str, Any]] = []
        for tc in response["tool_calls"]:
            if "function" in tc:
                func_name = tc["function"].get("name", "")
                raw_args = tc["function"]["arguments"]
                args = _validate_tool_args(func_name, raw_args)
                normalized.append({
                    "name": func_name,
                    "args": args,
                    "id": tc.get("id"),
                })
            else:
                normalized.append(tc)
        ai_kwargs["tool_calls"] = normalized

    ai_msg = AIMessage(**ai_kwargs)

    logger.info(
        "agent_node: response has_content=%s has_tool_calls=%s",
        bool(response.get("content")), bool(response.get("tool_calls")),
    )

    # Build hitl_payload if the LLM called a user-facing tool
    result: dict[str, Any] = {"messages": [ai_msg]}
    if response.get("tool_calls"):
        for tc in response["tool_calls"]:
            name = tc.get("function", {}).get("name", "") if "function" in tc else tc.get("name", "")
            if name in USER_FACING_NAMES:
                raw_args = tc.get("function", {}).get("arguments", "{}") if "function" in tc else tc.get("args", {})
                args = _validate_tool_args(name, raw_args)
                if name == "ask_user":
                    result["hitl_payload"] = {
                        "type": "ask_user",
                        "message": args.get("message", ""),
                        "options": args.get("options", []),
                    }
                elif name == "present_plan":
                    result["hitl_payload"] = {
                        "type": "present_plan",
                        "message": args.get("message", ""),
                        "plan": args.get("plan", {}),
                    }
                elif name == "present_booking":
                    result["hitl_payload"] = {
                        "type": "present_booking",
                        "message": args.get("message", ""),
                        "orders": args.get("orders", []),
                        "total_amount": args.get("total_amount", 0),
                    }
                break  # only process the first user-facing tool

    return result


# ── 路由判断 ──

USER_FACING_NAMES = {"ask_user", "present_plan", "present_booking"}
INTERNAL_NAMES = {"update_extract_result", "update_itinerary"}


def route_after_agent(state: PlanState) -> str:
    """根据 LLM 的最后一个 message 决定路由。

    - 调用了 user-facing tool → "hitl"
    - 调用了其他 tool → "tools"
    - 纯文本回复（无 tool_calls）→ "end"
    """
    msgs = state.get("messages", [])
    if not msgs:
        return "end"

    last_msg = msgs[-1]

    # Check for tool_calls
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    if tool_calls:
        names = {tc["name"] if isinstance(tc, dict) else tc.name for tc in tool_calls}
        if names & USER_FACING_NAMES:
            return "hitl"
        return "tools"

    return "end"
