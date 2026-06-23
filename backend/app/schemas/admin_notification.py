"""B 端业务通知 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AdminNotificationCreate(BaseModel):
    """创建面向管理员的业务通知。"""

    type: str = Field(..., min_length=1, max_length=32)
    title: str = Field(..., min_length=1, max_length=255)
    body: str | None = None
    action_url: str | None = Field(None, max_length=512)
    ticket_id: UUID | None = None
