"""Core runtime schemas for the production agent refactor."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlanRequestEnvelope(BaseModel):
    """Normalized request envelope for a single plan run."""

    request_id: str
    plan_id: str
    session_id: str
    user_id: str
    user_input: str
    lat: float
    lng: float
    created_at: datetime
    idempotency_key: str
    graph_version: str
    client_version: str | None = None
    debug: bool = False


class AgentError(BaseModel):
    """Structured error emitted by agent nodes and services."""

    code: str
    message: str
    node_name: str
    retryable: bool = False
    detail: dict[str, str] = Field(default_factory=dict)
