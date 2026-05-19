"""Runtime event schemas used by streaming and audit trails."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RuntimeEventType = Literal[
    "node_started",
    "node_succeeded",
    "node_failed",
    "interrupt_requested",
    "interrupt_resumed",
    "tool_called",
    "tool_finished",
    "plan_completed",
]


class RuntimeEvent(BaseModel):
    """A single event emitted by the runtime for observability."""

    event_id: str
    run_id: str
    plan_id: str
    node_name: str
    event_type: RuntimeEventType
    timestamp: datetime
    payload: dict = Field(default_factory=dict)
