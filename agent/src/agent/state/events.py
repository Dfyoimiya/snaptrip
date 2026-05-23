"""Event helpers for the new runtime layer."""

from __future__ import annotations

import uuid
from datetime import datetime

from agent.schemas.events import RuntimeEvent, RuntimeEventType


def build_runtime_event(
    *,
    run_id: str,
    plan_id: str,
    node_name: str,
    event_type: RuntimeEventType,
    payload: dict | None = None,
) -> RuntimeEvent:
    """Build a runtime event with consistent ids and timestamps."""

    return RuntimeEvent(
        event_id=str(uuid.uuid4()),
        run_id=run_id,
        plan_id=plan_id,
        node_name=node_name,
        event_type=event_type,
        timestamp=datetime.utcnow(),
        payload=payload or {},
    )
