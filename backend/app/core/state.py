"""Plan 状态机 —— 7 状态 FSM + 守卫条件 + 转移矩阵。

状态流转规则:
  IDLE ─[create_request]──→ DRAFTING
  DRAFTING ─[intent_ready]──→ PLANNING
  PLANNING ─[plan_draft_ready]──→ CONFIRMING
  CONFIRMING ─[user_confirm_all]──→ EXECUTING
  CONFIRMING ─[user_objection/slot_replacement]──→ CONFIRMING (可重入)
  CONFIRMING ─[fallback_triggered]──→ CONFIRMING (增量重规划)
  EXECUTING ─[execution_success]──→ DONE
  EXECUTING ─[execution_partial_fail + retry<N]──→ CONFIRMING
  EXECUTING ─[execution_partial_fail + retry≥N]──→ FAILED
  任意状态 ─[timeout>300s]──→ FAILED

守卫条件:
  _guard_create_request: 用户输入非空 + 经纬度有效范围
  _guard_intent_ready: Intent 产出非空
  _guard_plan_draft_ready: slots 非空 + 总费用 ≤ 预算
  _guard_fallback_available: Fallback 重试次数 < 上限
  _guard_fallback_exhausted: Fallback 重试次数 ≥ 上限

同状态多守卫: EXECUTING + EXECUTION_PARTIAL_FAIL 有两个目标状态，
transition() 按顺序尝试守卫，首个通过即生效。

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum

from app.core.constants import (
    CONFIRM_TIMEOUT_S,
    FALLBACK_MAX_RETRY,
    GLOBAL_TIMEOUT_S,
    PlanStatus,
)


class StateEvent(StrEnum):
    CREATE_REQUEST = "create_request"
    INTENT_READY = "intent_ready"
    CONTEXT_READY = "context_ready"
    PLAN_DRAFT_READY = "plan_draft_ready"
    USER_CONFIRM_ALL = "user_confirm_all"
    USER_OBJECTION = "user_objection"
    SLOT_REPLACEMENT = "slot_replacement"
    EXECUTION_SUCCESS = "execution_success"
    EXECUTION_PARTIAL_FAIL = "execution_partial_fail"
    FALLBACK_SUCCESS = "fallback_success"
    FALLBACK_EXHAUSTED = "fallback_exhausted"
    TIMEOUT = "timeout"


@dataclass
class StateRecord:
    plan_id: str
    state: str = PlanStatus.IDLE
    fallback_retry_count: int = 0
    locked_slot_indices: set[int] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    last_transition_at: float = field(default_factory=time.time)


# 守卫条件函数 (前向声明)
def _guard_create_request(record: StateRecord, payload: dict) -> bool:
    user_input = payload.get("user_input", "")
    lat = payload.get("lat", 0)
    lng = payload.get("lng", 0)
    return bool(user_input) and -90 <= lat <= 90 and -180 <= lng <= 180


def _guard_intent_ready(_record: StateRecord, payload: dict) -> bool:
    return payload.get("intent") is not None


def _guard_plan_draft_ready(record: StateRecord, payload: dict) -> bool:
    slots = payload.get("slots", [])
    total_cost = payload.get("total_cost", 0)
    budget = payload.get("budget", float("inf"))
    return len(slots) > 0 and total_cost <= budget


def _guard_confirm_all(record: StateRecord, payload: dict) -> bool:
    return True


def _guard_fallback_available(record: StateRecord, payload: dict) -> bool:
    return record.fallback_retry_count < FALLBACK_MAX_RETRY


def _guard_fallback_exhausted(record: StateRecord, payload: dict) -> bool:
    return record.fallback_retry_count >= FALLBACK_MAX_RETRY


class PlanStateMachine:
    TRANSITIONS: list[tuple] = [
        (PlanStatus.IDLE, StateEvent.CREATE_REQUEST, PlanStatus.DRAFTING, _guard_create_request),
        (
            PlanStatus.DRAFTING, StateEvent.INTENT_READY,
            PlanStatus.PLANNING, _guard_intent_ready,
        ),
        (
            PlanStatus.PLANNING, StateEvent.PLAN_DRAFT_READY,
            PlanStatus.CONFIRMING, _guard_plan_draft_ready,
        ),
        (
            PlanStatus.CONFIRMING, StateEvent.USER_CONFIRM_ALL,
            PlanStatus.EXECUTING, _guard_confirm_all,
        ),
        (PlanStatus.CONFIRMING, StateEvent.USER_OBJECTION, PlanStatus.CONFIRMING, None),
        (PlanStatus.CONFIRMING, StateEvent.SLOT_REPLACEMENT, PlanStatus.CONFIRMING, None),
        (PlanStatus.EXECUTING, StateEvent.EXECUTION_SUCCESS, PlanStatus.DONE, None),
        (
            PlanStatus.EXECUTING, StateEvent.EXECUTION_PARTIAL_FAIL,
            PlanStatus.CONFIRMING, _guard_fallback_available,
        ),
        (
            PlanStatus.EXECUTING, StateEvent.EXECUTION_PARTIAL_FAIL,
            PlanStatus.FAILED, _guard_fallback_exhausted,
        ),
    ]

    GLOBAL_TIMEOUT_STATES: dict[str, str] = {
        PlanStatus.DRAFTING: PlanStatus.FAILED,
        PlanStatus.PLANNING: PlanStatus.FAILED,
        PlanStatus.CONFIRMING: PlanStatus.FAILED,
        PlanStatus.EXECUTING: PlanStatus.FAILED,
    }

    def __init__(self):
        self._records: dict[str, StateRecord] = {}

    def get_or_create(self, plan_id: str) -> StateRecord:
        if plan_id not in self._records:
            self._records[plan_id] = StateRecord(plan_id=plan_id)
        return self._records[plan_id]

    def can_transition(self, record: StateRecord, event: StateEvent, payload: dict | None = None) -> bool:
        for from_s, evt, _to_s, guard in self.TRANSITIONS:
            if from_s == record.state and evt == event and (guard is None or guard(record, payload or {})):
                return True
        return False

    def transition(self, record: StateRecord, event: StateEvent, payload: dict | None = None) -> str:
        for from_s, evt, to_s_str, guard in self.TRANSITIONS:
            if from_s == record.state and evt == event:
                if guard is None or guard(record, payload or {}):
                    to_s: str = to_s_str
                    record.state = to_s
                    record.last_transition_at = time.time()
                    return to_s
                raise ValueError(f"Guard failed: {record.state} + {event}")
        raise ValueError(f"No transition: {record.state} + {event}")

    def tick_timeout(self, record: StateRecord) -> str | None:
        elapsed = time.time() - record.created_at
        if elapsed > GLOBAL_TIMEOUT_S:
            target = self.GLOBAL_TIMEOUT_STATES.get(record.state)
            if target:
                record.state = target
                record.last_transition_at = time.time()
                return target
        return None

    def is_confirm_stale(self, record: StateRecord) -> bool:
        if record.state != PlanStatus.CONFIRMING:
            return False
        return (time.time() - record.last_transition_at) > CONFIRM_TIMEOUT_S
