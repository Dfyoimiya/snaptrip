"""Checkpoint Schema —— Slot 粒度检查点"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LockedSlot(BaseModel):
    slot_index: int
    confirmed_at: datetime | None = None
    booking_id: str | None = None


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
    locked_slots: list[LockedSlot] = Field(default_factory=list)
    tentative_slots: list[TentativeSlot] = Field(default_factory=list)
    shadow_candidates: list[ShadowSlot] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
