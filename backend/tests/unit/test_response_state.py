"""Typed API response assembly tests."""

from __future__ import annotations

from agent.state.response import state_to_response


def test_state_to_response_prefers_revised_draft_and_notification():
    response = state_to_response(
        {
            "plan_id": "p1",
            "status": "done",
            "request": {"user_input": "去喝咖啡"},
            "draft": {
                "plan_id": "p1",
                "version": 1,
                "slots": [],
                "total_cost": 100,
                "total_time_min": 120,
                "confidence": 0.7,
            },
            "repair": {
                "revised_draft": {
                    "plan_id": "p1",
                    "version": 2,
                    "slots": [],
                    "total_cost": 80,
                    "total_time_min": 90,
                    "confidence": 0.6,
                }
            },
            "notification": {
                "share_card": {
                    "url": "https://snaptrip.cn/cards/p1",
                    "message": "ok",
                },
                "delivered": True,
            },
        }
    )

    assert response.plan_id == "p1"
    assert response.query_text == "去喝咖啡"
    assert response.total_cost == 80
    assert response.total_time_min == 90
    assert response.share_card is not None
    assert response.share_card.url.endswith("/p1")
