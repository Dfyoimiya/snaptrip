"""
【客服域 Pydantic Schema】— C2B 智能客服请求/响应模型

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
#  退货资格校验
# ============================================================================


class ReturnEligibilityRequest(BaseModel):
    """退货资格校验请求"""

    order_id: UUID = Field(..., description="订单ID")


class ReturnEligibilityResponse(BaseModel):
    """退货资格校验响应"""

    eligible: bool = Field(..., description="是否可退货")
    reason: str | None = Field(None, description="不可退货原因")
    order_status: int = Field(..., description="当前订单状态码")
    order_status_text: str = Field(..., description="当前订单状态文本")
    days_since_delivery: int | None = Field(None, description="签收后天数")
    policy_max_days: int = Field(default=15, description="退货政策允许最大天数")


# ============================================================================
#  提交退货申请
# ============================================================================


class ReturnSubmitRequest(BaseModel):
    """提交退货申请"""

    order_id: UUID = Field(..., description="订单ID")
    reason: str = Field(..., min_length=1, max_length=500, description="退货原因")
    description: str | None = Field(None, max_length=2000, description="问题描述")
    product_count: int = Field(default=1, ge=1, description="退货数量")


class ReturnSubmitResponse(BaseModel):
    """退货申请提交结果"""

    return_id: UUID = Field(..., description="退货申请ID")
    order_id: UUID
    status: int = Field(default=0, description="状态: 0=待处理")
    return_amount: Decimal
    message: str = Field(default="退货申请已提交，等待审核")


# ============================================================================
#  退款进度查询
# ============================================================================


class RefundStatusResponse(BaseModel):
    """退款进度响应"""

    return_id: UUID | None = Field(None, description="退货申请ID")
    order_id: UUID
    has_return_request: bool = Field(..., description="是否有退货申请")
    return_status: int | None = Field(None, description="退货状态: 0=待处理 1=已退货 2=已拒绝 3=已退款")
    return_status_text: str
    refund_amount: Decimal | None = None
    applied_at: datetime | None = None
    handled_at: datetime | None = None
    handle_note: str | None = None


# ============================================================================
#  工单
# ============================================================================


class CreateTicketRequest(BaseModel):
    """创建客服工单"""

    title: str = Field(..., min_length=1, max_length=255, description="工单标题")
    description: str = Field(..., min_length=1, max_length=2000, description="问题描述")
    order_id: UUID | None = Field(None, description="关联订单ID")
    type: str = Field(default="inquiry", description="工单类型: complaint/refund/inquiry/other")
    priority: str = Field(default="normal", description="优先级: normal/urgent/critical")


class TicketResponse(BaseModel):
    """工单响应"""

    id: UUID
    order_id: UUID | None = None
    type: str
    status: str
    priority: str
    title: str
    description: str | None = None
    resolution: str | None = None
    satisfaction_score: int | None = None
    escalated_to: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================================
#  补偿优惠券
# ============================================================================


class CompensationRequest(BaseModel):
    """发放补偿优惠券请求"""

    order_id: UUID = Field(..., description="关联订单ID")
    amount: Decimal = Field(..., ge=0, le=99999.99, description="优惠券面额")
    reason: str = Field(..., max_length=500, description="补偿原因")
    member_id: UUID = Field(..., description="会员ID")


class CompensationResponse(BaseModel):
    """补偿优惠券结果"""

    coupon_id: UUID
    amount: Decimal
    reason: str
    message: str


# ============================================================================
#  物流查询
# ============================================================================


class LogisticsResponse(BaseModel):
    """物流信息响应 —— 当前为 stub，接入真实物流API后扩展"""

    order_id: UUID
    order_status: int
    order_status_text: str
    tracking_number: str | None = None
    carrier: str | None = None
    estimated_delivery: datetime | None = None
    delivered_at: datetime | None = None
    note: str = "物流详情需接入快递鸟/菜鸟等第三方API"


# ============================================================================
#  投诉校验
# ============================================================================


class ComplaintValidationResponse(BaseModel):
    """投诉合理性校验结果"""

    valid: bool = Field(..., description="投诉是否合理")
    order_exists: bool = Field(..., description="订单是否存在")
    order_belongs_to_user: bool = Field(..., description="订单是否属于该用户")
    order_status_ok: bool = Field(..., description="订单状态是否允许投诉")
    previous_complaints: int = Field(default=0, description="该订单已有投诉次数")
    suggested_action: str = Field(..., description="建议操作")


# ============================================================================
#  会话记忆 (Phase 3)
# ============================================================================


class SessionSummaryRequest(BaseModel):
    """保存客服会话摘要请求"""

    session_id: str = Field(..., description="会话ID")
    intent: str | None = Field(None, description="客服意图")
    summary_text: str = Field(..., min_length=1, description="LLM 生成的会话摘要")
    resolution_status: str = Field(default="unknown", description="解决状态")
    satisfaction_score: int | None = Field(None, ge=1, le=5, description="满意度 1-5")
    ticket_id: str | None = Field(None, description="关联工单ID")
    order_id: str | None = Field(None, description="关联订单ID")
    conversation_turns: int = Field(default=0, description="对话轮数")
    tools_called: list[str] | None = Field(None, description="调用的工具列表")
    key_entities: dict | None = Field(None, description="关键实体")
    emotion_trajectory: str | None = Field(None, description="情绪轨迹")


class SessionSummaryResponse(BaseModel):
    """会话摘要响应"""

    id: str
    session_id: str
    intent: str | None = None
    summary_text: str
    resolution_status: str
    satisfaction_score: int | None = None
    ticket_id: str | None = None
    order_id: str | None = None
    conversation_turns: int
    tools_called: list | None = None
    emotion_trajectory: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class CsHistoryResponse(BaseModel):
    """用户 CS 历史响应"""

    user_id: str
    sessions: list[SessionSummaryResponse]
