"""Helpers for typed post-confirmation runtime state."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from app.schemas.agent.state import (
    CheckpointSnapshot,
    ConfirmationState,
    RepairState,
    UserChangeRequest,
)
from app.schemas.plan import POI, PlanDraft, PlanSlot, RevisedPlan, SlotDiff


def confirmation_from_resume(resume: dict[str, Any] | None) -> dict[str, Any]:
    """Build structured confirmation state from resume payload."""

    payload = resume or {}
    decision = payload.get("decision", "confirmed")
    slot_index = payload.get("slot_index")
    locked_slots = list(payload.get("locked_slots") or [])
    rejected_slots = list(payload.get("rejected_slots") or [])
    instruction = payload.get("instruction", "")
    change_requests = list(payload.get("change_requests") or [])

    reject_decisions = {"objection", "partial_change", "rejected"}
    if slot_index is not None and slot_index not in rejected_slots and decision in reject_decisions:
        rejected_slots.append(slot_index)

    if decision == "confirmed":
        status = "confirmed"
    elif decision in {"objection", "partial_change"}:
        status = "partial_change"
    else:
        status = "rejected"

    normalized_requests = [
        UserChangeRequest(**item).model_dump() if isinstance(item, dict) else item
        for item in change_requests
    ]
    if instruction:
        normalized_requests.append(
            UserChangeRequest(
                slot_index=slot_index,
                instruction=instruction,
                replace_only=bool(payload.get("replace_only", False)),
            ).model_dump()
        )

    return ConfirmationState(
        status=status,
        locked_slots=locked_slots,
        rejected_slots=rejected_slots,
        user_change_requests=[
            UserChangeRequest(**item) if isinstance(item, dict) else item
            for item in normalized_requests
        ],
        confirmed_at=datetime.utcnow() if status == "confirmed" else None,
    ).model_dump()


def route_from_confirmation(state: Mapping[str, Any]) -> Literal["execution_engine", "planning_engine", "end"]:
    """Resolve the next graph branch from confirmation state or legacy decision."""

    confirmation = state.get("confirmation") or {}
    status = confirmation.get("status")
    if status == "confirmed":
        return "execution_engine"
    if status in {"partial_change", "rejected"}:
        return "planning_engine"

    decision = state.get("user_decision", "confirmed")
    if decision == "confirmed":
        return "execution_engine"
    if decision in {"objection", "partial_change", "rejected"}:
        return "planning_engine"
    return "end"


def maybe_apply_confirmation_replan(state: Mapping[str, Any]) -> dict[str, Any] | None:
    """Apply a lightweight slot-level replan from confirmation state.

    This keeps the mainline moving before the full planning engine is migrated to
    consume typed change requests directly.
    """

    confirmation_raw = state.get("confirmation") or {}
    if confirmation_raw.get("status") not in {"partial_change", "rejected"}:
        return None

    draft_raw = state.get("draft")
    if not draft_raw:
        return None

    draft = PlanDraft(**draft_raw) if isinstance(draft_raw, dict) else draft_raw
    rejected_slots = confirmation_raw.get("rejected_slots", [])
    changed = False

    for slot_index in rejected_slots:
        if slot_index < 0 or slot_index >= len(draft.slots):
            continue
        replacement = _find_replacement_poi(draft, slot_index)
        if replacement is None:
            continue
        old_slot = draft.slots[slot_index]
        draft.slots[slot_index] = PlanSlot(
            sequence=old_slot.sequence,
            poi=replacement,
            time_range=old_slot.time_range,
            action=old_slot.action,
            estimated_cost=replacement.avg_price,
            move_time_min=old_slot.move_time_min,
            confidence=max(0.5, old_slot.confidence - 0.1),
            shadow_id=old_slot.shadow_id,
        )
        changed = True

    if not changed:
        return None

    draft.total_cost = sum(slot.estimated_cost for slot in draft.slots)
    draft.version += 1
    return draft.model_dump()


def build_repair_state(
    *,
    draft: dict[str, Any] | PlanDraft | None,
    revision: dict[str, Any] | None,
    locked_slots: list[int],
    retry_count: int,
) -> dict[str, Any]:
    """Create typed repair state from a revised plan payload."""

    base_draft = _as_plan_draft(draft)
    revised_plan = RevisedPlan(**revision) if revision else None
    checkpoint = None
    if base_draft is not None:
        mutable_slots = [idx for idx in range(len(base_draft.slots)) if idx not in locked_slots]
        checkpoint = CheckpointSnapshot(
            version=base_draft.version,
            locked_slots=locked_slots,
            mutable_slots=mutable_slots,
            draft=base_draft,
        )

    diffs: list[SlotDiff] = []
    revised_draft = None
    if revised_plan is not None:
        revised_draft = revised_plan.plan
        diffs = revised_plan.diff_patch

    return RepairState(
        retry_count=retry_count,
        checkpoint=checkpoint,
        revised_draft=revised_draft,
        diffs=diffs,
        exhausted=revised_draft is None,
    ).model_dump()


def notification_state_from_share_card(share_card: Mapping[str, Any] | None) -> dict[str, Any]:
    """Build typed notification state from legacy share card payload."""

    return {
        "share_card": share_card or None,
        "delivered": bool(share_card),
    }


def _find_replacement_poi(draft: PlanDraft, slot_index: int) -> POI | None:
    from app.data.seed_pois import SEED_POIS

    slot = draft.slots[slot_index]
    if slot.shadow_id:
        shadow = next((poi for poi in SEED_POIS if poi.id == slot.shadow_id), None)
        if shadow is not None:
            return POI(**shadow.model_dump())

    candidates = [
        poi for poi in SEED_POIS
        if poi.type == slot.poi.type and poi.id != slot.poi.id
    ]
    if not candidates:
        return None
    return POI(**candidates[0].model_dump())


def _as_plan_draft(draft: Mapping[str, Any] | PlanDraft | None) -> PlanDraft | None:
    if draft is None:
        return None
    if isinstance(draft, PlanDraft):
        return draft
    return PlanDraft(**draft)
