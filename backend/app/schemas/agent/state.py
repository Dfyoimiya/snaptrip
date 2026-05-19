"""Production-oriented runtime state schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent.runtime import AgentError, PlanRequestEnvelope
from app.schemas.plan import CandidatePool, EnrichedIntent, ExecutionResult, PlanDraft, POI, ShareCard, TimeRange

PlanRuntimeStatus = Literal[
    "created",
    "drafting",
    "planning",
    "confirming",
    "executing",
    "repairing",
    "done",
    "failed",
]


class MemoryFeatures(BaseModel):
    """Aggregated memory features injected into downstream planning."""

    dominant_scene: str | None = None
    boosted_type_prefs: list[str] = Field(default_factory=list)
    boosted_mood_prefs: list[str] = Field(default_factory=list)
    profile_vector: list[float] = Field(default_factory=list)


class CandidateReason(BaseModel):
    """Explain why a candidate was recalled or promoted."""

    poi_id: str
    recall_source: Literal["city_filter", "memory_boost", "fallback", "manual"]
    score: float
    matched_constraints: list[str] = Field(default_factory=list)


class UserChangeRequest(BaseModel):
    """Structured user edit request for partial re-planning."""

    slot_index: int | None = None
    instruction: str = ""
    replace_only: bool = False


class ConfirmationState(BaseModel):
    """Human-in-the-loop confirmation state."""

    status: Literal["pending", "confirmed", "rejected", "partial_change"] = "pending"
    locked_slots: list[int] = Field(default_factory=list)
    rejected_slots: list[int] = Field(default_factory=list)
    user_change_requests: list[UserChangeRequest] = Field(default_factory=list)
    confirmed_at: datetime | None = None


class ToolExecutionRecord(BaseModel):
    """Tool-level execution record for one invocation."""

    invocation_id: str
    slot_index: int
    tool_name: str
    layer: int
    status: Literal["success", "failure", "timeout", "skipped"]
    error_code: str | None = None
    error_message: str | None = None
    booking_id: str | None = None
    latency_ms: int = 0
    depends_on: list[str] = Field(default_factory=list)


class ExecutionState(BaseModel):
    """Normalized execution state separate from graph internals."""

    run_id: str
    status: Literal["full_success", "partial_success", "full_failure"]
    tool_records: list[ToolExecutionRecord] = Field(default_factory=list)
    confirmed_bookings: dict[int, str] = Field(default_factory=dict)
    failed_slot_indices: list[int] = Field(default_factory=list)
    total_elapsed_ms: int = 0
    raw_result: ExecutionResult | None = None


class SlotAlternative(BaseModel):
    """Alternative POI precomputed for a slot."""

    poi_id: str
    prechecked: bool = False
    score: float = 0.0


class DraftSlotSnapshot(BaseModel):
    """A richer slot snapshot used by the new planning layer."""

    sequence: int
    poi: POI
    time_range: TimeRange
    action: str
    estimated_cost: int = 0
    move_time_min: int = 0
    confidence: float = 0.0
    rationale: list[str] = Field(default_factory=list)
    alternatives: list[SlotAlternative] = Field(default_factory=list)


class SlotDiff(BaseModel):
    """Diff between two plan drafts during repair."""

    slot_index: int
    old_poi_id: str
    new_poi_id: str
    old_poi_name: str
    new_poi_name: str
    time_shift_min: int = 0


class CheckpointSnapshot(BaseModel):
    """Checkpoint persisted before or after human confirmation."""

    version: int
    locked_slots: list[int] = Field(default_factory=list)
    mutable_slots: list[int] = Field(default_factory=list)
    draft: PlanDraft


class RepairState(BaseModel):
    """Repair/replan lifecycle state."""

    retry_count: int = 0
    checkpoint: CheckpointSnapshot | None = None
    revised_draft: PlanDraft | None = None
    diffs: list[SlotDiff] = Field(default_factory=list)
    exhausted: bool = False


class NotificationState(BaseModel):
    """Notification output state."""

    share_card: ShareCard | None = None
    delivered: bool = False


class PlanRuntimeState(BaseModel):
    """Typed graph state for the production refactor."""

    request: PlanRequestEnvelope
    status: PlanRuntimeStatus = "created"
    intent: dict | None = None
    context_profile: EnrichedIntent | None = None
    memory_features: MemoryFeatures | None = None
    candidate_pool: CandidatePool | None = None
    draft: PlanDraft | None = None
    confirmation: ConfirmationState | None = None
    execution: ExecutionState | None = None
    repair: RepairState | None = None
    notification: NotificationState | None = None
    locked_slots: list[int] = Field(default_factory=list)
    errors: list[AgentError] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    seed: int = 0
