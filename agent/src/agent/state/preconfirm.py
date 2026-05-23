"""Helpers for migrating pre-confirmation graph state to typed runtime fields."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from snaptrip_shared.core.constants import PlanStatus

from agent.protocol import AgentContext, AgentResult
from agent.schemas.state import ConfirmationState, MemoryFeatures


def make_agent_result(agent_name: str, data: dict[str, Any]) -> AgentResult:
    """Create a lightweight AgentResult for history chaining."""

    return AgentResult(agent_name=agent_name, status="success", data=data)


def context_from_state(state: Mapping[str, Any], history: list[AgentResult] | None = None) -> AgentContext:
    """Build agent context from mixed legacy + typed runtime state."""

    request = state.get("request") or {}
    return AgentContext(
        plan_id=state.get("plan_id", request.get("plan_id", "")),
        session_id=state.get("session_id", request.get("session_id", "")),
        user_id=state.get("user_id", request.get("user_id", "default")),
        user_input=state.get("user_input", request.get("user_input", "")),
        lat=state.get("lat", request.get("lat", 39.9219)),
        lng=state.get("lng", request.get("lng", 116.4435)),
        state=state.get("status", PlanStatus.IDLE),
        history=history or [],
    )


def candidate_pool_from_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Read candidate pool from graph state."""

    return state.get("candidate_pool") or {}


def context_profile_from_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Read enriched context profile from graph state."""

    return state.get("context_profile") or {}


def build_memory_features(enriched: Mapping[str, Any]) -> dict[str, Any]:
    """Derive a minimal typed memory feature view from enriched intent."""

    intent = enriched.get("intent", {}) if isinstance(enriched, dict) else {}
    return MemoryFeatures(
        dominant_scene=intent.get("scene_type"),
        boosted_type_prefs=intent.get("type_prefs", []),
        boosted_mood_prefs=intent.get("mood_prefs", []),
        profile_vector=enriched.get("profile_vector", []) if isinstance(enriched, dict) else [],
    ).model_dump()


def pending_confirmation() -> dict[str, Any]:
    """Create default pending confirmation state."""

    return ConfirmationState(status="pending").model_dump()
