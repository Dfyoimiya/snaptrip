"""运行时事件 schema —— HITL 用户消息 + SSE 事件。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Option Item ─────────────────────────────────────────────


class OptionItem(BaseModel):
    """单个选项 —— 用于前端渲染选项卡片。

    label:       选项文本
    value:       选项值（不填则等于 label）
    description: 选项描述/副标题（灰字小号，帮助用户理解选项含义）
    """

    label: str = Field(description="选项文本")
    value: str = Field(default="", description="选项值（不填则等于 label）")
    description: str | None = Field(default=None, description="选项描述/副标题")


# ── HITL 用户消息 Payload ───────────────────────────────────


class QuestionPayload(BaseModel):
    """ask_user → 前端渲染问题卡片（澄清/协商）。

    options 为空列表表示自由文本输入（无预设选项）。
    """

    type: Literal["question"] = "question"
    message: str = Field(description="LLM 对用户说的话 (支持 Markdown)")
    options: list[OptionItem] = Field(default_factory=list)


class PlanConfirmPayload(BaseModel):
    """present_plan → 前端渲染方案确认卡片。

    默认操作选项: 确认 / 修改 / 换一个
    """

    type: Literal["plan_confirm"] = "plan_confirm"
    message: str = Field(description="方案说明文字 (支持 Markdown)")
    plan: dict[str, Any] = Field(description="结构化行程方案 (PlanOutline)")
    options: list[OptionItem] = Field(
        default_factory=lambda: [
            OptionItem(label="确认方案", value="confirmed", description="开始预订"),
            OptionItem(label="修改方案", value="modified", description="调整细节"),
            OptionItem(label="换一个", value="rejected", description="生成新方案"),
        ]
    )


class BookingOrderItem(BaseModel):
    """单个预订订单项。"""

    order_type: str = Field(description="预订类型 (restaurant/activity/cake/flowers)")
    poi_name: str = Field(description="POI/餐厅名称")
    guest_count: int = Field(description="人数")
    time: str | None = Field(default=None, description="预订时间 HH:MM")
    amount_cny: float = Field(default=0.0, description="费用（元）")
    note: str | None = Field(default=None, description="备注")


class BookingConfirmPayload(BaseModel):
    """present_booking → 前端渲染预订确认卡片。

    默认操作选项: 确认预订 / 取消
    """

    type: Literal["booking_confirm"] = "booking_confirm"
    message: str = Field(description="预订说明文字 (支持 Markdown)")
    orders: list[BookingOrderItem] = Field(description="待确认的预订项目列表")
    total_amount: float = Field(description="总费用（元）")
    options: list[OptionItem] = Field(
        default_factory=lambda: [
            OptionItem(label="确认预订", value="confirmed", description="执行预订"),
            OptionItem(label="取消", value="rejected", description="放弃本次预订"),
        ]
    )


# ── 联合类型 ────────────────────────────────────────────────

UserMessagePayload = QuestionPayload | PlanConfirmPayload | BookingConfirmPayload


# ── Runtime Event ───────────────────────────────────────────


class RuntimeEvent(BaseModel):
    plan_id: str = ""
    node_name: str = ""
    event_type: str = ""
    event_id: str = Field(default_factory=lambda: f"evt-{datetime.now(timezone.utc).timestamp()}")
    payload: UserMessagePayload | dict[str, Any] | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
