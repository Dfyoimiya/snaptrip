"""Helpers for building the new runtime request/state envelope."""

from __future__ import annotations

import uuid
from datetime import datetime

from snaptrip_shared.schemas.plan import PlanCreateRequest

from agent.schemas.runtime import PlanRequestEnvelope
from agent.schemas.state import PlanRuntimeState

GRAPH_VERSION = "v2-refactor-bootstrap"


def build_request_envelope(
    req: PlanCreateRequest,
    *,
    plan_id: str | None = None,
    session_id: str | None = None,
    graph_version: str = "v2-refactor-bootstrap",
) -> PlanRequestEnvelope:
    """Create a normalized request envelope for graph execution."""

    normalized_plan_id = plan_id or str(uuid.uuid4())[:8]
    normalized_session_id = session_id or str(uuid.uuid4())[:8]
    request_id = str(uuid.uuid4())
    idempotency_key = f"{req.user_id}:{req.user_input}:{normalized_plan_id}"

    return PlanRequestEnvelope(
        request_id=request_id,
        plan_id=normalized_plan_id,
        session_id=normalized_session_id,
        user_id=req.user_id,
        user_input=req.user_input,
        lat=req.lat,
        lng=req.lng,
        created_at=datetime.utcnow(),
        idempotency_key=idempotency_key,
        graph_version=graph_version,
    )


def build_initial_runtime_state(
    req: PlanCreateRequest,
    *,
    plan_id: str | None = None,
    session_id: str | None = None,
    graph_version: str = "v2-refactor-bootstrap",
) -> PlanRuntimeState:
    """Create the typed runtime state used by the new runtime layer."""

    envelope = build_request_envelope(
        req,
        plan_id=plan_id,
        session_id=session_id,
        graph_version=graph_version,
    )
    return PlanRuntimeState(request=envelope, status="created")
