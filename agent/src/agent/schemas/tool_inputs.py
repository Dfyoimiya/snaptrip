"""Pydantic 工具输入模型 —— 类型安全的工具 Schema 生成。

每个模型对应一个工具的输入参数，通过 model_json_schema() 自动生成
OpenAI function-calling 格式的 JSON Schema。

Author: SnapTrip Team
Date: 2026-05-31
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from agent.schemas.extract import (
    HardConstraints,
    SoftConstraints,
    UpdateExtractResultInput,
    UserIntent,
    UserRequirements,
)


# ── Helper ────────────────────────────────────────────────


def to_openai_tool(name: str, description: str, model: type[BaseModel]) -> dict[str, Any]:
    """将 Pydantic BaseModel 转换为 OpenAI function-calling 工具定义。"""
    schema = model.model_json_schema()
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema,
        },
    }


# ── User-facing tools (触发 HITL) ──────────────────────────


class AskUserInput(BaseModel):
    """ask_user 工具输入 —— 向用户提问。"""

    message: str = Field(description="你想对用户说的话")
    options: list[str] | None = Field(default=None, description="可选建议选项")


class PlanOutline(BaseModel):
    """plan 子对象 —— 结构化行程方案概要。"""

    summary: str | None = Field(default=None, description="方案摘要")
    slots: list[dict[str, Any]] | None = Field(default=None, description="行程 slot 列表")
    total_cost: float | None = Field(default=None, description="预估总费用")


class PresentPlanInput(BaseModel):
    """present_plan 工具输入 —— 展示最终规划方案。"""

    message: str = Field(description="方案说明文字")
    plan: PlanOutline = Field(description="完整的结构化行程方案")


class BookingOrder(BaseModel):
    """booking order 子对象 —— 单个预订项目。"""

    order_type: Literal["restaurant", "activity"] | None = Field(
        default=None, description="预订类型"
    )
    poi_name: str | None = Field(default=None, description="POI/餐厅名称")
    guest_count: int | None = Field(default=None, description="人数")
    time: str | None = Field(default=None, description="预订时间 HH:MM")
    amount_cny: float | None = Field(default=None, description="费用（元）")
    note: str | None = Field(default=None, description="备注")


class PresentBookingInput(BaseModel):
    """present_booking 工具输入 —— 展示预订确认表单。"""

    message: str = Field(description="预订说明文字")
    orders: list[BookingOrder] = Field(description="待确认的预订项目列表")
    total_amount: float = Field(description="总费用")


class UpdateItineraryInput(BaseModel):
    """update_itinerary 工具输入 —— 将选定方案写入当前行程。"""

    summary: str | None = Field(default=None, description="行程摘要")
    slots: list[dict[str, Any]] | None = Field(default=None, description="行程 slot 列表")
    total_cost: float | None = Field(default=None, description="总费用")
    total_time_min: float | None = Field(default=None, description="总耗时（分钟）")
    activity_name: str | None = Field(default=None, description="活动名称")
    restaurant_name: str | None = Field(default=None, description="餐厅名称")


# ── Tool definition tables ────────────────────────────────

# Extract 阶段工具（extract_node 使用）
EXTRACT_TOOL_DEFS: list[dict[str, Any]] = [
    to_openai_tool(
        "update_extract_result",
        "逐步更新意图提取结果。每次调用合并新提取的字段到已有结果中 (增量合并，"
        "只传本次新获得的字段，list 字段会合并去重)。"
        "只在从对话中获得新信息时才调用。不要覆盖用户已确认的旧值。",
        UpdateExtractResultInput,
    ),
    to_openai_tool(
        "ask_user",
        "向用户提问以澄清缺失信息。仅当必须的信息无法从对话中推断时使用。"
        "参数 message 是你想问用户的话，options 是可选的建议选项列表。",
        AskUserInput,
    ),
]

USER_FACING_TOOL_DEFS: list[dict[str, Any]] = [
    to_openai_tool(
        "ask_user",
        "向用户提问。当你需要澄清需求、协商约束调整、或信息不足时主动调用。"
        "参数 message 是你想问用户的话，options 是可选的建议选项列表。",
        AskUserInput,
    ),
    to_openai_tool(
        "present_plan",
        "向用户展示最终规划方案。用户确认后才能执行预订。"
        "plan 参数必须包含完整的结构化行程：summary, slots "
        "(每个slot有 time_start, time_end, action, place, estimated_cost), total_cost。",
        PresentPlanInput,
    ),
    to_openai_tool(
        "present_booking",
        "向用户展示预订确认表单。在用户确认行程方案后，将需要预订的项目"
        "（餐厅订座、活动门票等）以结构化表单展示给用户确认。"
        "用户确认后才会通过 mock_order_create/mock_payment_charge 执行实际预订。",
        PresentBookingInput,
    ),
]

INTERNAL_TOOL_DEFS: list[dict[str, Any]] = [
    to_openai_tool(
        "update_extract_result",
        "从对话中提取/更新用户意图、需求、约束信息。增量合并模式——只传本次新提取的字段，"
        "list 字段会合并去重。不要覆盖已确认的值。",
        UpdateExtractResultInput,
    ),
    to_openai_tool(
        "update_itinerary",
        "将选定的方案更新为当前行程，用于执行前的状态记录。",
        UpdateItineraryInput,
    ),
]
