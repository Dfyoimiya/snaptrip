"""Graph runtime state migration tests."""

from __future__ import annotations

from app.agent_runtime import preconfirm_state

def test_context_from_state_prefers_request_envelope():
    state = {
        "request": {
            "plan_id": "p_req",
            "session_id": "s_req",
            "user_id": "u_req",
            "user_input": "喝咖啡",
            "lat": 31.2,
            "lng": 121.4,
        },
        "status": "planning",
    }

    context = preconfirm_state.context_from_state(state)

    assert context.plan_id == "p_req"
    assert context.session_id == "s_req"
    assert context.user_id == "u_req"
    assert context.user_input == "喝咖啡"
    assert context.lat == 31.2
    assert context.lng == 121.4


def test_build_memory_features_from_enriched_intent():
    enriched = {
        "intent": {
            "scene_type": "date",
            "type_prefs": ["cafe"],
            "mood_prefs": ["安静"],
        },
        "profile_vector": [0.1, 0.2],
    }

    features = preconfirm_state.build_memory_features(enriched)

    assert features["dominant_scene"] == "date"
    assert features["boosted_type_prefs"] == ["cafe"]
    assert features["boosted_mood_prefs"] == ["安静"]
    assert features["profile_vector"] == [0.1, 0.2]


def test_context_profile_and_candidate_pool_use_new_keys():
    state = {
        "context_profile": {"intent": {"city": "上海"}},
        "candidate_pool": {"total": 3},
    }

    assert preconfirm_state.context_profile_from_state(state)["intent"]["city"] == "上海"
    assert preconfirm_state.candidate_pool_from_state(state)["total"] == 3


def test_context_profile_and_candidate_pool_return_empty_when_missing():
    assert preconfirm_state.context_profile_from_state({}) == {}
    assert preconfirm_state.candidate_pool_from_state({}) == {}


def test_pending_confirmation_defaults_to_pending():
    confirmation = preconfirm_state.pending_confirmation()
    assert confirmation["status"] == "pending"
