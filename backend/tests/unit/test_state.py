"""状态机守卫条件 + 转移矩阵测试"""

import time

import pytest

from app.core.constants import FALLBACK_MAX_RETRY, GLOBAL_TIMEOUT_S
from app.core.state import (
    PlanStatus,
    StateEvent,
    StateRecord,
    _guard_create_request,
    _guard_fallback_available,
    _guard_fallback_exhausted,
    _guard_intent_ready,
    _guard_plan_draft_ready,
)


class TestGuardConditions:
    def test_create_request_valid(self):
        payload = {"user_input": "想去故宫", "lat": 39.9, "lng": 116.4}
        assert _guard_create_request(StateRecord(plan_id="p1"), payload) is True

    def test_create_request_empty_input(self):
        payload = {"user_input": "", "lat": 39.9, "lng": 116.4}
        assert _guard_create_request(StateRecord(plan_id="p1"), payload) is False

    def test_create_request_bad_latitude(self):
        payload = {"user_input": "hello", "lat": 999, "lng": 116.4}
        assert _guard_create_request(StateRecord(plan_id="p1"), payload) is False

    def test_create_request_bad_longitude(self):
        payload = {"user_input": "hello", "lat": 39, "lng": 999}
        assert _guard_create_request(StateRecord(plan_id="p1"), payload) is False

    def test_intent_ready_with_intent(self):
        assert _guard_intent_ready(StateRecord(plan_id="p1"), {"intent": {"city": "北京"}}) is True

    def test_intent_ready_without_intent(self):
        assert _guard_intent_ready(StateRecord(plan_id="p1"), {}) is False

    def test_plan_draft_no_slots(self):
        payload = {"slots": [], "total_cost": 0, "budget": 300}
        assert _guard_plan_draft_ready(StateRecord(plan_id="p1"), payload) is False

    def test_plan_draft_over_budget(self):
        payload = {"slots": [1], "total_cost": 500, "budget": 300}
        assert _guard_plan_draft_ready(StateRecord(plan_id="p1"), payload) is False

    def test_plan_draft_valid(self):
        payload = {"slots": [1], "total_cost": 200, "budget": 300}
        assert _guard_plan_draft_ready(StateRecord(plan_id="p1"), payload) is True

    def test_fallback_available(self):
        record = StateRecord(plan_id="p1", fallback_retry_count=0)
        assert _guard_fallback_available(record, {}) is True

    def test_fallback_exhausted(self):
        record = StateRecord(plan_id="p1", fallback_retry_count=FALLBACK_MAX_RETRY)
        assert _guard_fallback_exhausted(record, {}) is True

    def test_fallback_not_exhausted(self):
        record = StateRecord(plan_id="p1", fallback_retry_count=0)
        assert _guard_fallback_exhausted(record, {}) is False


class TestStateMachine:
    def test_create_record_idle(self, state_machine):
        record = state_machine.get_or_create("p1")
        assert record.state == PlanStatus.IDLE
        assert record.fallback_retry_count == 0

    def test_same_plan_returns_same_record(self, state_machine):
        r1 = state_machine.get_or_create("p1")
        r2 = state_machine.get_or_create("p1")
        assert r1 is r2

    def test_transition_idle_to_drafting(self, state_machine):
        record = state_machine.get_or_create("p1")
        new = state_machine.transition(record, StateEvent.CREATE_REQUEST,
                                       {"user_input": "hi", "lat": 39, "lng": 116})
        assert new == PlanStatus.DRAFTING
        assert record.state == PlanStatus.DRAFTING

    def test_transition_drafting_to_planning(self, state_machine):
        record = state_machine.get_or_create("p1")
        state_machine.transition(record, StateEvent.CREATE_REQUEST,
                                 {"user_input": "hi", "lat": 39, "lng": 116})
        new = state_machine.transition(record, StateEvent.INTENT_READY, {"intent": {}})
        assert new == PlanStatus.PLANNING

    def test_full_happy_path(self, state_machine):
        record = state_machine.get_or_create("p1")
        state_machine.transition(record, StateEvent.CREATE_REQUEST,
                                 {"user_input": "hi", "lat": 39, "lng": 116})
        state_machine.transition(record, StateEvent.INTENT_READY, {"intent": {}})
        state_machine.transition(record, StateEvent.PLAN_DRAFT_READY,
                                 {"slots": [1], "total_cost": 200, "budget": 500})
        state_machine.transition(record, StateEvent.USER_CONFIRM_ALL)
        state_machine.transition(record, StateEvent.EXECUTION_SUCCESS)
        assert record.state == PlanStatus.DONE

    def test_invalid_transition_raises(self, state_machine):
        record = state_machine.get_or_create("p1")
        with pytest.raises(ValueError):
            state_machine.transition(record, StateEvent.INTENT_READY)

    def test_guard_failed_raises(self, state_machine):
        record = state_machine.get_or_create("p1")
        with pytest.raises(ValueError):
            state_machine.transition(record, StateEvent.CREATE_REQUEST, {"user_input": "", "lat": 39, "lng": 116})

    def test_confirming_reentrant(self, state_machine):
        record = state_machine.get_or_create("p1")
        state_machine.transition(record, StateEvent.CREATE_REQUEST, {"user_input": "hi", "lat": 39, "lng": 116})
        state_machine.transition(record, StateEvent.INTENT_READY, {"intent": {}})
        state_machine.transition(record, StateEvent.PLAN_DRAFT_READY, {"slots": [1], "total_cost": 200, "budget": 300})
        assert record.state == PlanStatus.CONFIRMING
        state_machine.transition(record, StateEvent.USER_OBJECTION)
        assert record.state == PlanStatus.CONFIRMING

    def test_timeout_leads_to_failed(self, state_machine):
        record = state_machine.get_or_create("p1")
        state_machine.transition(record, StateEvent.CREATE_REQUEST, {"user_input": "hi", "lat": 39, "lng": 116})
        record.created_at = time.time() - GLOBAL_TIMEOUT_S - 1
        result = state_machine.tick_timeout(record)
        assert result == PlanStatus.FAILED
        assert record.state == PlanStatus.FAILED

    def test_timeout_not_triggered_when_fresh(self, state_machine):
        record = state_machine.get_or_create("p1")
        state_machine.transition(record, StateEvent.CREATE_REQUEST, {"user_input": "hi", "lat": 39, "lng": 116})
        result = state_machine.tick_timeout(record)
        assert result is None

    def test_is_confirm_stale(self, state_machine):
        record = state_machine.get_or_create("p1")
        state_machine.transition(record, StateEvent.CREATE_REQUEST, {"user_input": "hi", "lat": 39, "lng": 116})
        state_machine.transition(record, StateEvent.INTENT_READY, {"intent": {}})
        state_machine.transition(record, StateEvent.PLAN_DRAFT_READY, {"slots": [1], "total_cost": 200, "budget": 300})
        record.last_transition_at = time.time() - 301
        assert state_machine.is_confirm_stale(record) is True

    def test_execution_partial_fail_to_confirming(self, state_machine):
        record = state_machine.get_or_create("p1")
        state_machine.transition(record, StateEvent.CREATE_REQUEST, {"user_input": "hi", "lat": 39, "lng": 116})
        state_machine.transition(record, StateEvent.INTENT_READY, {"intent": {}})
        state_machine.transition(record, StateEvent.PLAN_DRAFT_READY, {"slots": [1], "total_cost": 200, "budget": 300})
        state_machine.transition(record, StateEvent.USER_CONFIRM_ALL)
        new = state_machine.transition(record, StateEvent.EXECUTION_PARTIAL_FAIL)
        assert new == PlanStatus.CONFIRMING

    def test_fallback_exhausted_to_failed(self, state_machine):
        record = state_machine.get_or_create("p1")
        record.fallback_retry_count = FALLBACK_MAX_RETRY
        state_machine.transition(record, StateEvent.CREATE_REQUEST, {"user_input": "hi", "lat": 39, "lng": 116})
        state_machine.transition(record, StateEvent.INTENT_READY, {"intent": {}})
        state_machine.transition(record, StateEvent.PLAN_DRAFT_READY, {"slots": [1], "total_cost": 200, "budget": 300})
        state_machine.transition(record, StateEvent.USER_CONFIRM_ALL)
        new = state_machine.transition(record, StateEvent.EXECUTION_PARTIAL_FAIL)
        assert new == PlanStatus.FAILED
