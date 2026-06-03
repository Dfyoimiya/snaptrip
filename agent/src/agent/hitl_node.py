"""HITL Node —— 人机交互中断节点。

从 hitl_payload 中提取展示信息，调用 LangGraph interrupt()。
用户响应后返回 agent 继续 ReAct 循环。

支持三种交互类型:
  - ask_user:      澄清/协商 → QuestionPayload
  - present_plan:  方案确认 → PlanConfirmPayload
  - present_booking: 预订确认 → BookingConfirmPayload

中断前通过 event_bus 发射 RuntimeEvent (SSE → 前端)：
  - ask_user         → event_type: "question"
  - present_plan     → event_type: "need_confirmation"
  - present_booking  → event_type: "confirm_booking"

Author: SnapTrip Team
Date: 2026-05-29
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import interrupt

from agent.schemas.events import (
    BookingConfirmPayload,
    BookingOrderItem,
    OptionItem,
    PlanConfirmPayload,
    QuestionPayload,
    RuntimeEvent,
    UserMessagePayload,
)
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)


def _get_event_bus():
    """获取 Runtime 中的 event_bus（可能为 None）。"""
    from agent.graph import _runtime
    if _runtime:
        return _runtime.event_bus
    return None


async def _emit_interrupt_event(
    plan_id: str,
    event_type: str,
    payload: UserMessagePayload,
) -> None:
    """发射 SSE RuntimeEvent 通知前端有中断请求。

    payload 已经过 Pydantic 校验，直接序列化发射。
    """
    event_bus = _get_event_bus()
    if event_bus is None:
        logger.debug("hitl_node: no event_bus, skipping SSE emit for %s", event_type)
        return

    event = RuntimeEvent(
        plan_id=plan_id,
        node_name="hitl",
        event_type=event_type,
        payload=payload,
    )
    try:
        await event_bus.emit(event)
        logger.info("hitl_node: emitted %s event for plan %s", event_type, plan_id)
    except Exception:
        logger.warning("hitl_node: failed to emit %s event", event_type, exc_info=True)


def _build_question_payload(raw: dict[str, Any]) -> QuestionPayload:
    """从 LLM 原始 tool call args 构建 QuestionPayload。

    将旧的 string list options 转换为 OptionItem 列表。
    """
    raw_options: list[Any] = raw.get("options") or []
    options: list[OptionItem] = []
    for opt in raw_options:
        if isinstance(opt, OptionItem):
            options.append(opt)
        elif isinstance(opt, dict):
            options.append(OptionItem(**opt))
        else:
            # 纯字符串选项 → label=value=字符串
            options.append(OptionItem(label=str(opt), value=str(opt)))

    return QuestionPayload(
        message=raw.get("message", ""),
        options=options,
    )


def _build_plan_confirm_payload(raw: dict[str, Any]) -> PlanConfirmPayload:
    """从 LLM 原始 tool call args 构建 PlanConfirmPayload。"""
    return PlanConfirmPayload(
        message=raw.get("message", ""),
        plan=raw.get("plan", {}),
        options=[
            OptionItem(label="确认方案", value="confirmed", description="开始预订"),
            OptionItem(label="修改方案", value="modified", description="调整细节"),
            OptionItem(label="换一个", value="rejected", description="生成新方案"),
        ],
    )


def _build_booking_confirm_payload(raw: dict[str, Any]) -> BookingConfirmPayload:
    """从 LLM 原始 tool call args 构建 BookingConfirmPayload。"""
    raw_orders: list[dict[str, Any]] = raw.get("orders") or []
    orders: list[BookingOrderItem] = []
    for o in raw_orders:
        if isinstance(o, BookingOrderItem):
            orders.append(o)
        elif isinstance(o, dict):
            orders.append(BookingOrderItem(**o))

    return BookingConfirmPayload(
        message=raw.get("message", ""),
        orders=orders,
        total_amount=raw.get("total_amount", 0),
        options=[
            OptionItem(label="确认预订", value="confirmed", description="执行预订"),
            OptionItem(label="取消", value="rejected", description="放弃本次预订"),
        ],
    )


async def hitl_node(state: PlanState) -> dict:
    """HITL 中断节点。

    从 state["hitl_payload"] 中提取展示信息，调用 interrupt()。
    用户响应后包装为 ToolMessage 注入消息历史（满足 API 对 tool_calls 完整性的要求）。

    中断前通过 event_bus 发射 RuntimeEvent (SSE → 前端)。

    Returns:
        {"messages": [ToolMessage(...)], "hitl_payload": None}
    """
    raw_payload = state.get("hitl_payload") or {}

    if not raw_payload:
        logger.warning("hitl_node called without hitl_payload")
        return {
            "messages": [HumanMessage(content=json.dumps({"error": "no hitl payload"}))],
            "hitl_payload": None,
        }

    # Extract tool_call_id from the last AIMessage for proper tool result linking
    tool_call_id = ""
    messages = state.get("messages", [])
    for m in reversed(messages):
        if isinstance(m, AIMessage) and hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                tc_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                if tc_name in ("ask_user", "present_plan", "present_booking"):
                    tool_call_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
                    break
            if tool_call_id:
                break

    plan_id = state.get("plan_id", "")
    hitl_type = raw_payload.get("type", "unknown")
    logger.info("hitl_node: type=%s plan_id=%s", hitl_type, plan_id)

    # ── 用 Pydantic 模型构建 payload ──
    user_payload: UserMessagePayload

    if hitl_type == "ask_user":
        user_payload = _build_question_payload(raw_payload)
        await _emit_interrupt_event(plan_id, "question", user_payload)

    elif hitl_type == "present_plan":
        user_payload = _build_plan_confirm_payload(raw_payload)
        await _emit_interrupt_event(plan_id, "need_confirmation", user_payload)

    elif hitl_type == "present_booking":
        user_payload = _build_booking_confirm_payload(raw_payload)
        await _emit_interrupt_event(plan_id, "confirm_booking", user_payload)

    else:
        logger.warning("hitl_node: unknown type=%s", hitl_type)
        return {
            "messages": [ToolMessage(
                content=json.dumps({"error": f"unknown hitl type: {hitl_type}"}),
                tool_call_id=tool_call_id,
            )],
            "hitl_payload": None,
        }

    # interrupt() 接收 Pydantic model → LangGraph 自动序列化
    user_response = interrupt(user_payload)

    logger.info(
        "hitl_node: user_response keys=%s",
        list(user_response.keys()) if isinstance(user_response, dict) else str(user_response)[:100],
    )

    # 将用户响应包装为 ToolMessage（满足 API 对 tool_calls 完整性的要求）
    if isinstance(user_response, dict):
        response_text = json.dumps(user_response, ensure_ascii=False)
    else:
        response_text = str(user_response)

    return {
        "messages": [ToolMessage(content=response_text, tool_call_id=tool_call_id)],
        "hitl_payload": None,  # 清除
    }
