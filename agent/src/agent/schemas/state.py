"""Production-oriented runtime state schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from snaptrip_shared.schemas.plan import (
    POI,
    CandidatePool,
    EnrichedIntent,
    ExecutionResult,
    PlanDraft,
    ShareCard,
    SlotDiff,
    TimeRange,
)

from agent.schemas.runtime import AgentError, PlanRequestEnvelope

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


# ── Real-Time Context Schemas ──────────────────────────────────────


class WeatherSnapshot(BaseModel):
    """Weather snapshot for a point in time."""

    condition: Literal["sunny", "cloudy", "rainy", "snowy", "stormy"]
    temperature_c: float
    outdoor_score: float = Field(
        ge=0.0, le=1.0, description="0.0=dangerous, 1.0=excellent for outdoor"
    )
    report_time: datetime


class TrafficIndex(BaseModel):
    """Real-time traffic congestion index."""

    overall: float = Field(ge=0.0, le=1.0, description="0.0=clear, 1.0=gridlock")
    by_corridor: dict[str, float] = Field(default_factory=dict)
    updated_at: datetime | None = None


class PeakCalendar(BaseModel):
    """Peak-hour pricing and special events."""

    hourly_multipliers: dict[int, float] = Field(default_factory=dict)
    special_events: list[str] = Field(default_factory=list)


class RealTimeContext(BaseModel):
    """Aggregated real-time context fetched by context_loader, refreshed by monitor_engine."""

    weather: WeatherSnapshot | None = None
    traffic_index: TrafficIndex | None = None
    peak_calendar: PeakCalendar | None = None


# ── POI Real-Time Status ───────────────────────────────────────────


class POIRealTimeStatus(BaseModel):
    """Real-time status attached to each POI during retrieval."""

    poi_id: str
    available_seats: int | None = None
    available_tickets: int | None = None
    queue_length: int = 0
    wait_minutes: int = 0
    peak_surcharge_pct: int = 0
    weather_penalty: float = 0.0
    open_now: bool = True
    closes_in_min: int = 9999
    data_freshness: datetime | None = None


# ── Constraint Propagation ─────────────────────────────────────────


class ConstraintEdge(BaseModel):
    """Constraint relationship between two slots."""

    from_slot: int
    to_slot: int
    constraint_type: Literal[
        "travel_time", "budget_cascade", "time_window", "type_diversity"
    ]
    min_value: float
    max_value: float
    current_value: float


class SlotConfidence(BaseModel):
    """Decomposed confidence for a single slot."""

    overall: float = Field(ge=0.0, le=1.0)
    availability_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    route_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    pricing_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    weather_confidence: float = Field(ge=0.0, le=1.0, default=1.0)


# ── Monitor & Alert Schemas ────────────────────────────────────────


class RouteCheck(BaseModel):
    """Route monitoring check between two slots."""

    from_slot: int
    to_slot: int
    baseline_travel_min: int
    current_travel_min: int = 0


class QueueCheck(BaseModel):
    """Queue monitoring check for a POI."""

    slot_index: int
    poi_id: str
    baseline_queue: int
    current_queue: int = 0


class BookingCheck(BaseModel):
    """Booking status monitoring check."""

    slot_index: int
    poi_id: str
    booking_id: str
    current_status: str = "confirmed"


class MonitorPlan(BaseModel):
    """Post-execution monitoring configuration."""

    poll_interval_s: int = 60
    routes_to_track: list[RouteCheck] = Field(default_factory=list)
    queues_to_track: list[QueueCheck] = Field(default_factory=list)
    bookings_to_track: list[BookingCheck] = Field(default_factory=list)
    deadline: datetime | None = None


class Alert(BaseModel):
    """Real-time alert emitted by monitor_engine."""

    alert_type: Literal[
        "traffic_delay",
        "queue_surge",
        "weather_change",
        "booking_cancelled",
        "poi_closed",
    ]
    severity: Literal["info", "warning", "critical"]
    slot_indices: list[int] = Field(default_factory=list)
    message: str = ""
    suggested_action: Literal["no_op", "partial_replan", "full_replan", "cancel"] = (
        "no_op"
    )


class ReplanTrigger(BaseModel):
    """Trigger for graph re-entry after monitor detects an anomaly."""

    scope: Literal["partial", "full"]
    affected_slot_indices: list[int] = Field(default_factory=list)
    recommended_alternatives: list[str] = Field(default_factory=list)
    auto_replan: bool = False


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
    # New fields from architecture evolution
    realtime_context: RealTimeContext | None = None
    poi_real_time_statuses: dict[str, POIRealTimeStatus] = Field(default_factory=dict)
    constraint_edges: list[ConstraintEdge] = Field(default_factory=list)
    slot_confidences: dict[int, SlotConfidence] = Field(default_factory=dict)
    monitor_plan: MonitorPlan | None = None
    alerts: list[Alert] = Field(default_factory=list)
    replan_trigger: ReplanTrigger | None = None
    # Existing fields
    locked_slots: list[int] = Field(default_factory=list)
    errors: list[AgentError] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    seed: int = 0
