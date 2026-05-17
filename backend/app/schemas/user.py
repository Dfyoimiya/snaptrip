"""用户中心 Pydantic Schemas。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class UserProfileUpdateIn(BaseModel):
    nickname: str | None = None
    avatar_url: str | None = None
    preferences: dict | None = None
    travel_style: str | None = None
    home_address: dict | None = None


class UserProfileOut(BaseModel):
    nickname: str
    avatar_url: str | None = None
    preferences: dict = Field(default_factory=dict)
    travel_style: str | None = None
    home_address: dict | None = None
    preference_embedding: list[float] | None = None


class PlanSlotOut(BaseModel):
    id: str
    poi_id: str
    time_start: datetime
    time_end: datetime
    slot_status: str
    booking_ref: str | None = None
    buffer_minutes: int

    @field_serializer("id")
    def serialize_id(self, v: Any) -> str:
        return str(v)


class PlanListOut(BaseModel):
    id: str
    title: str
    status: str
    date_range: dict | None = None
    group_type: str
    created_at: datetime

    @field_serializer("id")
    def serialize_id(self, v: Any) -> str:
        return str(v)


class PlanDetailOut(PlanListOut):
    slots: list[PlanSlotOut] = Field(default_factory=list)
    checkpoints: list[dict] = Field(default_factory=list)
    adjustments: list[dict] = Field(default_factory=list)


class PaginatedPlans(BaseModel):
    items: list[PlanListOut]
    total: int
    page: int
    page_size: int
