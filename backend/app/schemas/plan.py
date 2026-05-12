"""Pydantic Schema —— 计划与 Agent 契约"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    start: datetime
    end: datetime


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
    child_friendly: bool = False
    dietary_tags: List[str] = Field(default_factory=list)
    capacity: Optional[int] = None


# ===== Agent 1: Intent Parser =====

class IntentInput(BaseModel):
    raw_query: str
    user_lat: float
    user_lng: float
    timestamp: Optional[datetime] = None
    session_id: Optional[str] = None


class IntentSchema(BaseModel):
    time_window: Optional[TimeRange] = None
    guest_count: int = 2
    budget: Optional[int] = None
    scene_type: str = "solo"
    type_prefs: List[str] = Field(default_factory=list)
    mood_prefs: List[str] = Field(default_factory=list)
    implicit_constraints: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    confidence: float = 0.5


# ===== Agent 2: Context Loader =====

class EnrichedIntent(BaseModel):
    intent: IntentSchema
    profile_vector: List[float] = Field(default_factory=list)
    family_profile: dict = Field(default_factory=dict)
    historical_rejections: List[str] = Field(default_factory=list)
    preferred_pace: str = "normal"
    user_id: str = "default"


# ===== Agent 3: Retrieval Engine =====

class CandidatePool(BaseModel):
    candidates: List[POI] = Field(default_factory=list)
    total: int = 0
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])


# ===== Agent 4: Planning Engine =====

class PlanSlot(BaseModel):
    sequence: int
    poi: POI
    time_range: TimeRange
    action: str
    estimated_cost: int = 0
    move_time_min: int = 0
    confidence: float = 0.5
    shadow_id: Optional[str] = None


class PlanDraft(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    slots: List[PlanSlot] = Field(default_factory=list)
    total_cost: int = 0
    total_time_min: int = 0
    confidence: float = 0.5
    version: int = 1


# ===== Agent 5: Execution Engine =====

class SlotExecutionResult(BaseModel):
    slot_index: int
    tool_name: str
    status: str
    booking_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    elapsed_ms: int = 0
    is_fallback: bool = False


class ExecutionResult(BaseModel):
    plan_id: str
    status: str
    slot_results: Dict[int, SlotExecutionResult] = Field(default_factory=dict)
    confirmed_bookings: Dict[int, str] = Field(default_factory=dict)
    failed_slots: List[FailedSlot] = Field(default_factory=list)
    layer_timings: Dict[int, int] = Field(default_factory=dict)
    total_elapsed_ms: int = 0


# ===== Agent 6: Fallback Engine =====

class ShadowCandidate(BaseModel):
    poi_id: str
    prechecked: bool = False
    estimated_availability: bool = False


class FailedSlot(BaseModel):
    slot_index: int
    tool_name: str
    error_code: str
    error_message: str
    shadow_candidate: Optional[ShadowCandidate] = None
    poi_id: str = ""


class SlotDiff(BaseModel):
    slot_index: int
    old_poi_id: str
    new_poi_id: str
    old_poi_name: str
    new_poi_name: str
    time_shift_min: int = 0


class RevisedPlan(BaseModel):
    plan: PlanDraft
    diff_patch: List[SlotDiff] = Field(default_factory=list)


# ===== Agent 8: Notify Engine =====

class ShareCard(BaseModel):
    url: str = ""
    message: str = ""
    ics_event: Optional[str] = None


# ===== Plan API =====

class PlanCreateRequest(BaseModel):
    user_input: str
    user_id: str = "default"
    lat: float = 39.9219
    lng: float = 116.4435
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class PlanResponse(BaseModel):
    plan_id: str
    query_text: str
    status: str
    total_cost: int = 0
    total_time_min: int = 0
    slots: List[PlanSlot] = Field(default_factory=list)
    share_card: Optional[ShareCard] = None
