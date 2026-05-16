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
    """FSM 事件枚举。

    每个事件对应一条状态转移边，由 Policy Engine 根据 Agent 输出触发。
    事件驱动 FSM 从当前状态转移到下一个合法状态。
    """
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
    """Plan 实例的运行时状态记录。

    每个活跃 Plan 对应一个 StateRecord，由 PlanStateMachine 管理。
    fallback_retry_count 跟踪当前 Plan 的 Fallback 重试次数。

    Attributes:
        plan_id: Plan 唯一标识
        state: 当前 FSM 状态
        fallback_retry_count: 已执行 Fallback 次数
        locked_slot_indices: 已确认不可变更的 Slot 索引集
        created_at: Plan 创建时间戳
        last_transition_at: 最后一次状态转移时间戳
    """
    plan_id: str
    state: str = PlanStatus.IDLE
    fallback_retry_count: int = 0
    locked_slot_indices: set[int] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    last_transition_at: float = field(default_factory=time.time)


# 守卫条件函数 (前向声明)
def _guard_create_request(record: StateRecord, payload: dict) -> bool:
    """用户输入非空 + 经纬度有效范围。

    Args:
        record: 当前 StateRecord
        payload: 含 user_input, lat, lng 的字典

    Returns:
        True 若输入有效，False 否则
    """
    user_input = payload.get("user_input", "")
    lat = payload.get("lat", 0)
    lng = payload.get("lng", 0)
    return bool(user_input) and -90 <= lat <= 90 and -180 <= lng <= 180


def _guard_intent_ready(_record: StateRecord, payload: dict) -> bool:
    """Intent 产出非空。

    Args:
        _record: 当前 StateRecord（未使用）
        payload: 含 intent 键的字典

    Returns:
        True 若 intent 字段非 None
    """
    return payload.get("intent") is not None


def _guard_plan_draft_ready(record: StateRecord, payload: dict) -> bool:
    """slots 非空 + 总费用 ≤ 预算。

    Args:
        record: 当前 StateRecord（未使用）
        payload: 含 slots, total_cost, budget 的字典

    Returns:
        True 若规划有效，False 否则
    """
    slots = payload.get("slots", [])
    total_cost = payload.get("total_cost", 0)
    budget = payload.get("budget", float("inf"))
    return len(slots) > 0 and total_cost <= budget


def _guard_confirm_all(record: StateRecord, payload: dict) -> bool:
    """无条件放行（单用户模式）。

    Args:
        record: 当前 StateRecord（未使用）
        payload: 载荷（未使用）

    Returns:
        始终返回 True
    """
    return True


def _guard_fallback_available(record: StateRecord, payload: dict) -> bool:
    """Fallback 重试次数 < 上限。

    Args:
        record: 当前 StateRecord
        payload: 载荷（未使用）

    Returns:
        True 若还可重试
    """
    return record.fallback_retry_count < FALLBACK_MAX_RETRY


def _guard_fallback_exhausted(record: StateRecord, payload: dict) -> bool:
    """Fallback 重试次数 ≥ 上限。

    Args:
        record: 当前 StateRecord
        payload: 载荷（未使用）

    Returns:
        True 若已耗尽重试次数
    """
    return record.fallback_retry_count >= FALLBACK_MAX_RETRY


class PlanStateMachine:
    """Plan 有限状态机。

    维护 7 个状态之间的合法转移，驱动 Plan 从 IDLE 到 DONE 或 FAILED。
    CONFIRMING 为可重入状态，支持增量重规划。

    Attributes:
        TRANSITIONS: 合法转移列表，每条为 (from_state, event, to_state, guard_func)
        GLOBAL_TIMEOUT_STATES: 各状态超时后应转移到的目标状态
    """
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
        """获取或创建 Plan 的 StateRecord。

        若 plan_id 已存在返回现有记录，否则创建 IDLE 状态的新记录。

        Args:
            plan_id: Plan 唯一标识

        Returns:
            对应的 StateRecord 实例
        """
        if plan_id not in self._records:
            self._records[plan_id] = StateRecord(plan_id=plan_id)
        return self._records[plan_id]

    def can_transition(self, record: StateRecord, event: StateEvent, payload: dict | None = None) -> bool:
        """检查给定事件是否可以触发状态转移。

        Args:
            record: 当前 StateRecord
            event: 待检查的事件
            payload: 守卫条件需要的载荷

        Returns:
            True 若存在合法转移且守卫条件满足"""
        for from_s, evt, _to_s, guard in self.TRANSITIONS:
            if from_s == record.state and evt == event and (guard is None or guard(record, payload or {})):
                return True
        return False

    def transition(self, record: StateRecord, event: StateEvent, payload: dict | None = None) -> str:
        """执行状态转移。

        遍历 TRANSITIONS 查找匹配的 (当前状态, 事件) 组合。
        若存在多个匹配（如同状态的 fallback_available / fallback_exhausted），
        按顺序尝试守卫条件，首个通过即生效。
        同时更新 last_transition_at 时间戳。

        Args:
            record: 当前 StateRecord（会被原地修改）
            event: 触发转移的事件
            payload: 守卫条件需要的载荷

        Returns:
            转移后的新状态名

        Raises:
            ValueError: 无匹配转移或所有守卫条件失败
        """
        last_error: str | None = None
        for from_s, evt, to_s_str, guard in self.TRANSITIONS:
            if from_s == record.state and evt == event:
                if guard is None or guard(record, payload or {}):
                    to_s: str = to_s_str
                    record.state = to_s
                    record.last_transition_at = time.time()
                    return to_s
                last_error = f"Guard failed: {record.state} + {event}"
        if last_error:
            raise ValueError(last_error)
        raise ValueError(f"No transition: {record.state} + {event}")

    def tick_timeout(self, record: StateRecord) -> str | None:
        """检查并触发全局超时。

        若 Plan 从创建至今超过 GLOBAL_TIMEOUT_S 秒，
        则将当前状态转移到 FAILED。

        Args:
            record: 当前 StateRecord

        Returns:
            若触发了超时转移返回新状态名，否则 None
        """
        elapsed = time.time() - record.created_at
        if elapsed > GLOBAL_TIMEOUT_S:
            target = self.GLOBAL_TIMEOUT_STATES.get(record.state)
            if target:
                record.state = target
                record.last_transition_at = time.time()
                return target
        return None

    def is_confirm_stale(self, record: StateRecord) -> bool:
        """检查 CONFIRMING 状态是否已超时。

        用于群体确认场景：若在 CONFIRMING 状态停留超过 CONFIRM_TIMEOUT_S 秒，
        则 Policy Engine 应强制裁决（多数决推进或失败）。

        Args:
            record: 当前 StateRecord

        Returns:
            True 若确认状态已超时
        """
        if record.state != PlanStatus.CONFIRMING:
            return False
        return (time.time() - record.last_transition_at) > CONFIRM_TIMEOUT_S
