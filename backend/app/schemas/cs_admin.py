"""
【客服管理域 Pydantic Schema】— 人工坐席后台请求/响应模型

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PaginationParams

# ============================================================================
#  工单管理
# ============================================================================


class TicketListQuery(PaginationParams):
    """工单列表查询参数"""

    status: str | None = Field(None, description="工单状态: open/in_progress/resolved/closed")
    priority: str | None = Field(None, description="优先级: normal/urgent/critical")
    type: str | None = Field(None, description="工单类型: complaint/refund/inquiry/other")
    assigned_agent_id: UUID | None = Field(None, description="按指派的坐席筛选")
    keyword: str | None = Field(None, description="标题/描述关键词搜索")


class TicketUpdateRequest(BaseModel):
    """更新工单"""

    status: str | None = Field(None, description="更新状态")
    priority: str | None = Field(None, description="更新优先级")
    tags: list[str] | None = Field(None, description="更新标签")
    resolution: str | None = Field(None, description="处理结果（关闭时填写）")
    satisfaction_score: int | None = Field(None, ge=1, le=5, description="满意度评分")


class TicketAssignRequest(BaseModel):
    """指派/认领工单"""

    agent_id: UUID | None = Field(None, description="坐席 ID，为 None 表示取消指派")
    action: str = Field(default="assign", description="assign/claim/unassign")


class TicketResolveRequest(BaseModel):
    """解决/关闭工单"""

    resolution: str = Field(..., min_length=1, description="处理结果")
    satisfaction_score: int | None = Field(None, ge=1, le=5)


class TicketResponse(BaseModel):
    """工单响应"""

    id: UUID
    order_id: UUID | None = None
    member_id: UUID
    type: str
    status: str
    priority: str
    title: str
    description: str | None = None
    resolution: str | None = None
    satisfaction_score: int | None = None
    escalated_to: str | None = None
    assigned_agent_id: UUID | None = None
    sla_deadline: datetime | None = None
    first_response_at: datetime | None = None
    tags: list | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================================
#  聊天消息
# ============================================================================


class CsMessageRequest(BaseModel):
    """发送聊天消息"""

    content: str = Field(..., min_length=1, description="消息正文")
    content_type: str = Field(default="text", description="内容类型: text/markdown")


class CsMessageResponse(BaseModel):
    """聊天消息响应"""

    id: UUID
    ticket_id: UUID
    sender_type: str
    sender_id: UUID | None = None
    content: str
    content_type: str
    metadata_: dict | None = Field(None, alias="metadata")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class CsMessageListResponse(BaseModel):
    """消息列表"""

    ticket_id: UUID
    messages: list[CsMessageResponse]


# ============================================================================
#  坐席状态
# ============================================================================


class AgentStatusUpdate(BaseModel):
    """更新坐席状态"""

    status: str = Field(..., description="online/offline/busy")
    current_ticket_id: UUID | None = Field(None, description="当前工单ID")


class AgentStatusResponse(BaseModel):
    """坐席状态响应"""

    admin_id: UUID
    status: str
    current_ticket_id: UUID | None = None
    max_concurrent: int
    last_heartbeat: datetime | None = None
    skills: list | None = None
    admin_name: str | None = None  # populated from users table

    model_config = {"from_attributes": True}


# ============================================================================
#  通知
# ============================================================================


class NotificationResponse(BaseModel):
    """通知响应"""

    id: UUID
    type: str
    ticket_id: UUID | None = None
    title: str
    body: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """通知列表"""

    items: list[NotificationResponse]
    unread_count: int
    total: int


# ============================================================================
#  客服统计
# ============================================================================


class CsStatsResponse(BaseModel):
    """客服统计数据"""

    total_tickets: int = Field(default=0, description="总工单数")
    open_count: int = Field(default=0, description="待处理")
    in_progress_count: int = Field(default=0, description="处理中")
    resolved_today: int = Field(default=0, description="今日解决")
    avg_response_minutes: float | None = Field(None, description="平均响应时间（分钟）")
    sla_breach_count: int = Field(default=0, description="SLA 超时数")
    online_agents: int = Field(default=0, description="在线坐席数")
