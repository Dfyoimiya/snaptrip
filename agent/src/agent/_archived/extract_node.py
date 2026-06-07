# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 ARCHIVED — TRIP PLANNING AGENT                      ║
# ║  Archived: 2026-06-07                                                        ║
# ║  Reason: Agent repurposed from local trip planning to new domain             ║
# ║  This file is preserved for reference but NOT imported by the framework.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

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

from agent.prompts.system import EXTRACT_SYSTEM_PROMPT
from agent.schemas.extract import ExtractResult
from agent.schemas.state import PlanState
from agent.schemas.tool_inputs import EXTRACT_TOOL_DEFS
from agent.utils import (
    get_llm_adapter,
    normalize_tool_calls_for_api,
    strip_orphan_tool_calls,
)

logger = logging.getLogger(__name__)


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
                msg["tool_calls"] = normalize_tool_calls_for_api(m.tool_calls)
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

    return strip_orphan_tool_calls(msgs)


async def extract_node(state: PlanState) -> dict:
    """Extract 阶段 LLM 推理节点。

    1. 构建消息（EXTRACT_SYSTEM_PROMPT + extract_result 上下文 + 对话历史）
    2. 调用 LLM（仅持有 EXTRACT_TOOLS）
    3. 返回 LLM 响应——后续由 tool_node 执行工具，由 route_after_extract 判定流转
    """
    llm = get_llm_adapter()

    messages = _build_extract_messages(state)

    logger.info(
        "extract_node: %d messages, %d tools",
        len(messages), len(EXTRACT_TOOL_DEFS),
    )

    ai_msg = await llm.chat(
        messages=messages,
        tools=EXTRACT_TOOL_DEFS,
        temperature=0.3,
        max_tokens=2048,
        timeout_s=120,
    )

    logger.info(
        "extract_node: response has_content=%s has_tool_calls=%s",
        bool(ai_msg.content), bool(ai_msg.tool_calls),
    )

    return {"messages": [ai_msg]}
