"""
【公告/通知 Pydantic Schema】— 请求/响应模型

Author: SnapTrip Team
Date: 2026-06-18
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NoticeCreate(BaseModel):
    """创建公告"""

    title: str = Field(..., min_length=1, max_length=200)
    content: str | None = None
    target_type: str = Field(default="ALL", pattern="^(ALL|CUSTOMER|MERCHANT)$")


class NoticeUpdate(BaseModel):
    """编辑公告 —— 全字段可选"""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    target_type: str | None = Field(None, pattern="^(ALL|CUSTOMER|MERCHANT)$")


class NoticeResponse(BaseModel):
    """公告详情"""

    id: UUID
    title: str
    content: str | None = None
    target_type: str
    status: int
    publish_time: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}
