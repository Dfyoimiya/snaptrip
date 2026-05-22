"""Post-confirmation typed runtime state tests."""

from __future__ import annotations

from agent_worker.app.agent.state.postconfirm import (
    build_repair_state,
    confirmation_from_resume,
    maybe_apply_confirmation_replan,
    route_from_confirmation,
)


def test_confirmation_from_resume_builds_partial_change():
    confirmation = confirmation_from_resume(
        {
            "decision": "objection",
            "slot_index": 1,
            "locked_slots": [0],
            "instruction": "换一个不要排队的",
            "replace_only": True,
        }
    )

    assert confirmation["status"] == "partial_change"
    assert confirmation["locked_slots"] == [0]
    assert confirmation["rejected_slots"] == [1]
    assert confirmation["user_change_requests"][0]["instruction"] == "换一个不要排队的"


def test_route_from_confirmation_prefers_typed_status():
    assert route_from_confirmation({"confirmation": {"status": "confirmed"}}) == "execution_engine"
    assert route_from_confirmation({"confirmation": {"status": "partial_change"}}) == "planning_engine"


def test_maybe_apply_confirmation_replan_swaps_shadow_slot():
    state = {
        "draft": {
            "plan_id": "p1",
            "version": 1,
            "slots": [
                {
                    "sequence": 0,
                    "poi": {
                        "id": "bj-001",
                        "name": "A",
                        "city": "北京",
                        "type": "restaurant",
                        "lat": 39.9,
                        "lng": 116.4,
                        "avg_price": 100,
                        "rating": 4.5,
                    },
                    "time_range": {
                        "start": "2026-05-13T14:00:00",
                        "end": "2026-05-13T15:00:00",
                    },
                    "action": "book_table",
                    "estimated_cost": 100,
                    "move_time_min": 0,
                    "confidence": 0.7,
                    "shadow_id": "bj-002",
                }
            ],
            "total_cost": 100,
            "total_time_min": 60,
            "confidence": 0.7,
        },
        "confirmation": {
            "status": "partial_change",
            "rejected_slots": [0],
            "locked_slots": [],
            "user_change_requests": [],
        },
    }

    revised = maybe_apply_confirmation_replan(state)

    assert revised is not None
    assert revised["version"] == 2
    assert revised["slots"][0]["poi"]["id"] != "bj-001"


def test_build_repair_state_includes_checkpoint_and_revision():
    repair = build_repair_state(
        draft={
            "plan_id": "p1",
            "version": 1,
            "slots": [],
            "total_cost": 0,
            "total_time_min": 0,
            "confidence": 0.7,
        },
        revision={
            "plan": {
                "plan_id": "p1",
                "version": 2,
                "slots": [],
                "total_cost": 0,
                "total_time_min": 0,
                "confidence": 0.6,
            },
            "diff_patch": [],
        },
        locked_slots=[0],
        retry_count=1,
    )

    assert repair["retry_count"] == 1
    assert repair["checkpoint"]["locked_slots"] == [0]
    assert repair["revised_draft"]["version"] == 2
