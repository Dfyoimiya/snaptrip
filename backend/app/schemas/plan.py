from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PlanCreateRequest(BaseModel):
    user_input: str = Field(..., description="用户自然语言输入")
    lat: float = Field(default=39.9219, description="用户纬度")
    lng: float = Field(default=116.4435, description="用户经度")
    start_time: Optional[datetime] = Field(default=None, description="计划开始时间")
    end_time: Optional[datetime] = Field(default=None, description="计划结束时间")


class POI(BaseModel):
    id: str
    name: str
    city: str
    type: str
    lat: float
    lng: float
    mood_tags: List[str] = Field(default_factory=list)
    avg_price: int = 0
    rating: float = 0.0
    business_hours: str = "09:00-22:00"


class PlanSlot(BaseModel):
    sequence: int
    time: str
    poi: POI
    action: str
    estimated_cost: int = 0
    move_time_min: int = 0


class PlanResponse(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    query_text: str
    status: str = "drafting"
    total_cost: int = 0
    total_time_min: int = 0
    slots: List[PlanSlot] = Field(default_factory=list)
