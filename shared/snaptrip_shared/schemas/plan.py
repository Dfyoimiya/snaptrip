"""Pydantic Schema —— 计划与 Agent 契约。

定义编排层 9 个 Agent 的输入输出数据结构（按 Agent 顺序排列）:
  1. IntentInput / IntentSchema     —— Intent Parser
  2. EnrichedIntent                 —— Context Loader + Memory Manager
  3. CandidatePool                  —— Retrieval Engine
  4. PlanSlot / PlanDraft           —— Planning Engine
  5. ExecutionResult / FailedSlot   —— Execution Engine
  6. ShadowCandidate / RevisedPlan  —— Fallback Engine
  7. ShareCard                      —— Notify Engine
  8. PlanCreateRequest / PlanResponse —— API 层

Schema 设计原则:
- 所有 Agent 的输入输出必须通过 Pydantic 校验
- 使用 | None 替代 Optional（Python 3.10+ 语法）
- 内存 Schema 传递（非序列化），仅在 API 边界做 JSON 转换

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import uuid
from datetime import datetime

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
    mood_tags: list[str] = Field(default_factory=list)
    avg_price: int = 0
    rating: float = 0.0
    business_hours: str = "09:00-22:00"
    child_friendly: bool = False
    dietary_tags: list[str] = Field(default_factory=list)
    capacity: int | None = None


# ===== Agent 1: Intent Parser =====


class IntentInput(BaseModel):
    raw_query: str
    user_lat: float
    user_lng: float
    timestamp: datetime | None = None
    session_id: str | None = None


class IntentSchema(BaseModel):
    time_window: TimeRange | None = None
    guest_count: int = 2
    budget: int | None = None
    scene_type: str = "solo"
    type_prefs: list[str] = Field(default_factory=list)
    mood_prefs: list[str] = Field(default_factory=list)
    implicit_constraints: list[str] = Field(default_factory=list)
    city: str | None = None
    confidence: float = 0.5


# ===== Agent 2: Context Loader =====


class EnrichedIntent(BaseModel):
    intent: IntentSchema
    profile_vector: list[float] = Field(default_factory=list)
    family_profile: dict = Field(default_factory=dict)
    historical_rejections: list[str] = Field(default_factory=list)
    preferred_pace: str = "normal"
    user_id: str = "default"


# ===== Agent 3: Retrieval Engine =====


class CandidatePool(BaseModel):
    candidates: list[POI] = Field(default_factory=list)
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
    shadow_id: str | None = None


class PlanDraft(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    slots: list[PlanSlot] = Field(default_factory=list)
    total_cost: int = 0
    total_time_min: int = 0
    confidence: float = 0.5
    version: int = 1


# ===== Single-Agent Plan Draft (LLM Structured Output) =====


class AgentPlanStep(BaseModel):
    """LLM 生成的单个工具调用步骤 —— Structured Output 约束"""

    tool_name: str = Field(description="工具名，必须来自可用工具列表")
    params: dict[str, object] = Field(default_factory=dict, description="工具参数，必须符合 input_schema")
    reasoning: str = Field(default="", description="选择此工具的思考过程，用于审计")


class AgentPlan(BaseModel):
    """LLM 生成的完整计划草案 —— ExecutionEngine 的输入"""

    steps: list[AgentPlanStep] = Field(description="按执行顺序排列的工具调用序列")
    estimated_duration_min: int = Field(default=30, ge=0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="LLM 对此计划的置信度")


# ===== Agent 5: Execution Engine =====


class SlotExecutionResult(BaseModel):
    slot_index: int
    tool_name: str
    status: str
    booking_id: str | None = None
    booking_ref: str | None = None
    physical_state: str = "pending"
    error_code: str | None = None
    error_message: str | None = None
    elapsed_ms: int = 0
    is_fallback: bool = False


class ExecutionResult(BaseModel):
    plan_id: str
    status: str
    slot_results: dict[int, SlotExecutionResult] = Field(default_factory=dict)
    confirmed_bookings: dict[int, str] = Field(default_factory=dict)
    failed_slots: list[FailedSlot] = Field(default_factory=list)
    layer_timings: dict[int, int] = Field(default_factory=dict)
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
    shadow_candidate: ShadowCandidate | None = None
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
    diff_patch: list[SlotDiff] = Field(default_factory=list)


# ===== Agent 8: Notify Engine =====


class ShareCard(BaseModel):
    url: str = ""
    message: str = ""
    ics_event: str | None = None


# ===== Plan API =====


class PlanCreateRequest(BaseModel):
    user_input: str
    user_id: str = "default"
    lat: float = 39.9219
    lng: float = 116.4435
    start_time: datetime | None = None
    end_time: datetime | None = None


class PlanResponse(BaseModel):
    plan_id: str
    query_text: str
    status: str
    total_cost: int = 0
    total_time_min: int = 0
    slots: list[PlanSlot] = Field(default_factory=list)
    share_card: ShareCard | None = None
