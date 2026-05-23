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
    repair: dict[str, Any] = state.get("repair") or {}
    revised: object = repair.get("revised_draft")
    if revised:
        if isinstance(revised, PlanDraft):
            revised_data: dict[str, Any] = revised.model_dump()
            return revised_data
        if isinstance(revised, dict):
            return revised
        return None

    draft: object = state.get("draft")
    if isinstance(draft, PlanDraft):
        draft_data: dict[str, Any] = draft.model_dump()
        return draft_data
    if isinstance(draft, dict):
        return draft
    return None


def _share_card_from_state(state: Mapping[str, Any]) -> dict[str, Any] | None:
    notification: dict[str, Any] = state.get("notification") or {}
    typed_share_card: object = notification.get("share_card")
    if typed_share_card:
        if isinstance(typed_share_card, ShareCard):
            d: dict[str, Any] = typed_share_card.model_dump()
            return d
        if isinstance(typed_share_card, dict):
            return typed_share_card
        return None
    sc: object = state.get("share_card")
    if isinstance(sc, dict):
        return sc
    return None
