"""Helpers for assembling API responses from mixed runtime state."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from snaptrip_shared.schemas.plan import PlanDraft, PlanResponse, PlanSlot, ShareCard


def state_to_response(state: Mapping[str, Any], query_text: str = "") -> PlanResponse:
    """Assemble API response preferring typed runtime state fields."""

    request = state.get("request") or {}
    draft = _draft_from_state(state)
    slots_raw = draft.get("slots", []) if draft else []
    slots = [PlanSlot(**slot) if isinstance(slot, dict) else slot for slot in slots_raw]

    share_card_data = _share_card_from_state(state)
    query = query_text or request.get("user_input", "")
    plan_id = state.get("plan_id") or request.get("plan_id", "")

    return PlanResponse(
        plan_id=plan_id,
        query_text=query,
        status=state.get("status", "idle"),
        total_cost=draft.get("total_cost", 0) if draft else 0,
        total_time_min=draft.get("total_time_min", 0) if draft else 0,
        slots=slots,
        share_card=ShareCard(**share_card_data) if share_card_data else None,
    )


def _draft_from_state(state: Mapping[str, Any]) -> dict[str, Any] | None:
    repair = state.get("repair") or {}
    revised = repair.get("revised_draft")
    if revised:
        if isinstance(revised, PlanDraft):
            return revised.model_dump()
        return revised  # type: ignore[no-any-return]

    draft = state.get("draft")
    if isinstance(draft, PlanDraft):
        return draft.model_dump()
    return draft


def _share_card_from_state(state: Mapping[str, Any]) -> dict[str, Any] | None:
    notification = state.get("notification") or {}
    typed_share_card = notification.get("share_card")
    if typed_share_card:
        if isinstance(typed_share_card, ShareCard):
            return typed_share_card.model_dump()
        return typed_share_card  # type: ignore[no-any-return]
    return state.get("share_card")
