"""Extract Node —— 意图提取阶段 LLM 推理节点。

Extract 阶段是 DAG 的第一个节点。内部是一个 LLM ReAct 微循环：
- LLM 持有 EXTRACT_TOOLS（update_extract_result + ask_user）
- 逐步从对话中提取意图/需求/约束
- 调用 ask_user 澄清缺失信息
- route_after_extract 判定是否可进入 plan 阶段

Author: SnapTrip Team
Date: 2026-05-31
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from pydantic import BaseModel

from agent.prompts.system import EXTRACT_SYSTEM_PROMPT
from agent.schemas.extract import ExtractResult, UpdateExtractResultInput
from agent.schemas.state import PlanState
from agent.schemas.tool_inputs import EXTRACT_TOOL_DEFS, AskUserInput
from snaptrip_shared.core.config import settings

logger = logging.getLogger(__name__)

# User-facing tools in extract phase
_EXTRACT_USER_FACING_NAMES = {"ask_user"}

# ── Tool arg Pydantic models for runtime validation ──
_TOOL_ARG_MODELS: dict[str, type[BaseModel]] = {
    "update_extract_result": UpdateExtractResultInput,
    "ask_user": AskUserInput,
}


def _build_extract_messages(state: PlanState) -> list[dict[str, Any]]:
    """从 PlanState 构建 extract 阶段 LLM 消息列表。

    注入当前 ExtractResult 上下文，帮助 LLM 了解已有信息和缺失字段。
    """
    msgs: list[dict[str, Any]] = [{"role": "system", "content": EXTRACT_SYSTEM_PROMPT}]

    # ── 注入用户位置 ──
    lat = state.get("lat")
    lng = state.get("lng")
    if lat is not None and lng is not None:
        msgs.append({
            "role": "system",
            "content": (
                f"用户当前位置: lat={lat}, lng={lng}。"
                "如果用户未提及城市，可结合位置推断所在城市。"
            ),
        })

    # ── 注入当前 ExtractResult 上下文 ──
    extract_result: ExtractResult | None = state.get("extract_result")
    if extract_result is not None:
        # 已有信息
        existing = extract_result.model_dump(exclude_none=True)
        msgs.append({
            "role": "system",
            "content": (
                "当前已提取的信息:\n"
                f"{json.dumps(existing, ensure_ascii=False, indent=2)}\n\n"
            ),
        })

        # 缺失字段提示
        if not extract_result.is_sufficient():
            missing = extract_result.missing_fields()
            question = extract_result.clarification_question()
            hint = (
                f"⚠️ 以下必要字段尚未提取: {', '.join(missing)}。\n"
            )
            if question:
                hint += f"建议向用户提问: {question}\n"
            hint += (
                "请在下一轮调用 ask_user 澄清缺失信息。"
                "如果用户已经提供了某些信息但你还没有提取，"
                "请先调用 update_extract_result。"
            )
            msgs.append({"role": "system", "content": hint})
    else:
        msgs.append({
            "role": "system",
            "content": (
                "尚未提取任何信息。请从用户对话中提取意图、需求、约束。"
                "如果信息不足，用 ask_user 主动提问。"
            ),
        })

    # ── 注入用户画像（如果有）──
    profile = state.get("user_profile")
    if profile and any(v for v in profile.values() if v):
        msgs.append({
            "role": "system",
            "content": f"用户画像: {json.dumps(profile, ensure_ascii=False)}",
        })

    # ── 对话历史 ──
    for m in state.get("messages", []):
        if isinstance(m, SystemMessage):
            msgs.append({"role": "system", "content": str(m.content)})
        elif isinstance(m, HumanMessage):
            msgs.append({"role": "user", "content": str(m.content)})
        elif isinstance(m, AIMessage):
            msg: dict[str, Any] = {
                "role": "assistant",
                "content": str(m.content) if m.content else None,
            }
            if hasattr(m, "tool_calls") and m.tool_calls:
                msg["tool_calls"] = _normalize_tool_calls_for_api(m.tool_calls)
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


def _normalize_tool_calls_for_api(tool_calls: list[Any]) -> list[dict[str, Any]]:
    """将 LangChain ToolCall 转换为 OpenAI API 格式。"""
    result: list[dict[str, Any]] = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            if "function" in tc:
                result.append(tc)
            else:
                name = tc.get("name", "")
                args = tc.get("args", {})
                result.append({
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(args, ensure_ascii=False)
                        if not isinstance(args, str) else args,
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
                    "arguments": json.dumps(args, ensure_ascii=False)
                    if not isinstance(args, str) else args,
                },
            })
    return result


def _safe_parse_json(raw: str) -> dict[str, Any]:
    """安全解析 LLM 返回的可能含多余内容的 JSON。"""
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
                "extract_node: malformed JSON in tool %s args, trying recovery", name,
            )
            recovered = _safe_parse_json(raw_args)
            if not recovered:
                logger.error(
                    "extract_node: unrecoverable JSON for tool %s: %s",
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
            "extract_node: Pydantic validation for %s failed, using raw args. "
            "Args: %s", name, str(args)[:200],
            exc_info=True,
        )
        return args


async def extract_node(state: PlanState) -> dict:
    """Extract 阶段 LLM 推理节点。

    1. 构建消息（EXTRACT_SYSTEM_PROMPT + extract_result 上下文 + 对话历史）
    2. 调用 LLM（仅持有 EXTRACT_TOOLS）
    3. 返回 LLM 响应——后续由 tool_node 执行工具，由 route_after_extract 判定流转
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

    messages = _build_extract_messages(state)

    logger.info(
        "extract_node: %d messages, %d tools",
        len(messages), len(EXTRACT_TOOL_DEFS),
    )

    response = await llm.chat(
        messages=messages,
        tools=EXTRACT_TOOL_DEFS,
        temperature=0.3,
        max_tokens=2048,
        timeout_s=120,
    )

    # ── 构造 AIMessage ──
    ai_kwargs: dict[str, Any] = {}
    if response.get("content"):
        ai_kwargs["content"] = response["content"]
    rc = response.get("reasoning_content")
    if rc:
        ai_kwargs["reasoning_content"] = rc
    if response.get("tool_calls"):
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
        "extract_node: response has_content=%s has_tool_calls=%s",
        bool(response.get("content")), bool(response.get("tool_calls")),
    )

    # ── 构建 hitl_payload（如果 LLM 调用了 ask_user）──
    result: dict[str, Any] = {"messages": [ai_msg]}
    if response.get("tool_calls"):
        for tc in response["tool_calls"]:
            name = tc.get("function", {}).get("name", "") if "function" in tc else tc.get("name", "")
            if name == "ask_user":
                raw_args = tc.get("function", {}).get("arguments", "{}") if "function" in tc else tc.get("args", {})
                args = _validate_tool_args(name, raw_args)
                result["hitl_payload"] = {
                    "type": "ask_user",
                    "message": args.get("message", ""),
                    "options": args.get("options", []),
                }
                break

    return result
