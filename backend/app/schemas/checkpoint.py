"""Checkpoint Schema —— Slot 粒度检查点"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LockedSlot(BaseModel):
    slot_index: int
    confirmed_at: Optional[datetime] = None
    booking_id: Optional[str] = None


class TentativeSlot(BaseModel):
    slot_index: int
    poi_id: str
    start_time: datetime
    end_time: datetime
    action: str


class ShadowSlot(BaseModel):
    slot_index: int
    alternative_poi_id: str
    prechecked: bool = False


class Checkpoint(BaseModel):
    plan_id: str
    version: int = 1
    state: str = "idle"
    locked_slots: List[LockedSlot] = Field(default_factory=list)
    tentative_slots: List[TentativeSlot] = Field(default_factory=list)
    shadow_candidates: List[ShadowSlot] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
