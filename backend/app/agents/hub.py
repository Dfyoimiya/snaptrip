"""Master Controller —— 编排层中央控制器。

负责单个 Plan 实例的完整生命周期管理，包含三个内核:
1. State Registry: 维护 7 状态 FSM，所有状态转移通过 PlanStateMachine 执行
2. Policy Engine: 基于当前状态 + Agent 输出 + 异常信号，裁决下一状态和激活的 Agent 列表
3. Checkpoint Manager: 以 Slot 为最小粒度的乐观检查点，确保增量重规划时的已确认/可变更边界

对外接口:
- init_plan(): 创建新 Plan，状态从 IDLE 转移到 DRAFTING
- decide(): 策略裁决，返回 PolicyDecision（目标状态 + Agent 列表）
- decide_execution_result(): 处理 ExecutionEngine 返回结果，路由 Fallback 或完成
- save_checkpoint(): 持久化 locked/tentative/shadow slots
- store_result(): 存储 Agent 执行结果，供后续 Agent 通过 context.history 获取

9 Agent 调度链: Intent → Context → Memory → Retrieval → Planning
                 → Consensus → Execution → Fallback → Notify

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from pydantic import BaseModel

from app.agents.protocol import AgentContext, AgentResult
from app.core.constants import FALLBACK_MAX_RETRY, PlanStatus
from app.core.state import PlanStateMachine, StateEvent, StateRecord
from app.schemas.checkpoint import Checkpoint, LockedSlot, ShadowSlot, TentativeSlot
from app.schemas.plan import ExecutionResult, PlanDraft, PlanSlot


class PolicyDecision(BaseModel):
    """策略裁决结果。

    Attributes:
        next_state: 裁决后的目标状态
        agents_to_activate: 下一状态需激活的 Agent 名称列表
        message: 裁决说明（超时/拒绝原因等）
    """
    next_state: str
    agents_to_activate: list[str]
    message: str = ""


class MasterController:

    def __init__(self):
        """初始化三内核：StateRegistry + PolicyEngine + CheckpointManager。"""
        self.state_machine = PlanStateMachine()
        self.checkpoints: dict[str, Checkpoint] = {}
        self.agent_results: dict[str, dict[str, AgentResult]] = {}
        self.drafts: dict[str, PlanDraft] = {}
        self.execution_results: dict[str, ExecutionResult] = {}

    # === State Registry ===

    def init_plan(self, plan_id: str, context: AgentContext) -> StateRecord:
        """创建新 Plan，状态从 IDLE 转移到 DRAFTING。

        校验用户输入和经纬度有效后，初始化 agent_results 存储。

        Args:
            plan_id: Plan 唯一标识
            context: 含 user_input, lat, lng 的执行上下文

        Returns:
            新创建的 StateRecord
        """
        record = self.state_machine.get_or_create(plan_id)
        payload = {"user_input": context.user_input, "lat": context.lat, "lng": context.lng}
        self.state_machine.transition(record, StateEvent.CREATE_REQUEST, payload)
        context.state = record.state
        context.plan_id = plan_id
        self.agent_results[plan_id] = {}
        return record

    def get_state(self, plan_id: str) -> StateRecord:
        """获取 Plan 的当前状态记录。

        Args:
            plan_id: Plan 唯一标识

        Returns:
            对应的 StateRecord
        """
        return self.state_machine.get_or_create(plan_id)

    # === Policy Engine ===

    def decide(self, record: StateRecord, event: StateEvent, payload: dict | None = None) -> PolicyDecision:
        """策略裁决：根据当前状态 + 事件返回下一步动作。

        先检查全局超时 → 再尝试状态转移 → 若拒绝则保持当前状态。

        Args:
            record: 当前 StateRecord
            event: 触发的事件
            payload: 守卫条件所需的载荷

        Returns:
            PolicyDecision 含目标状态和激活的 Agent 列表
        """
        timeout_state = self.state_machine.tick_timeout(record)
        if timeout_state:
            return PolicyDecision(
                next_state=timeout_state, agents_to_activate=[], message="Global timeout"
            )
        if self.state_machine.can_transition(record, event, payload):
            new_state = self.state_machine.transition(record, event, payload)
            agents = self._agents_for_state(new_state)
            return PolicyDecision(next_state=new_state, agents_to_activate=agents)
        return PolicyDecision(
            next_state=record.state, agents_to_activate=[],
            message=f"Transition denied: {record.state}+{event}"
        )

    def decide_execution_result(self, record: StateRecord, result: ExecutionResult) -> PolicyDecision:
        """执行结果裁决：根据 ExecutionResult 路由 Fallback 或完成。

        full_success → DONE
        partial_success 且 retry<N → Fallback → CONFIRMING
        其他 → FAILED

        Args:
            record: 当前 StateRecord
            result: ExecutionEngine 的执行结果

        Returns:
            PolicyDecision 含下一步动作
        """
        if result.status == "full_success":
            return self.decide(record, StateEvent.EXECUTION_SUCCESS)
        elif result.status == "partial_success":
            record.fallback_retry_count += 1
            if record.fallback_retry_count < FALLBACK_MAX_RETRY:
                return self.decide(record, StateEvent.EXECUTION_PARTIAL_FAIL)
        return PolicyDecision(next_state=PlanStatus.FAILED, agents_to_activate=[])

    def _agents_for_state(self, state: str) -> list[str]:
        """状态→Agent 映射表。

        DRAFTING: IntentParser + ContextLoader + MemoryManager
        PLANNING: RetrievalEngine + PlanningEngine
        EXECUTING: ExecutionEngine
        DONE: NotifyEngine
        """
        mapping: dict[str, list[str]] = {
            PlanStatus.DRAFTING: ["intent_parser", "context_loader", "memory_manager"],
            PlanStatus.PLANNING: ["retrieval_engine", "planning_engine"],
            PlanStatus.CONFIRMING: [],
            PlanStatus.EXECUTING: ["execution_engine"],
            PlanStatus.DONE: ["notify_engine"],
            PlanStatus.FAILED: [],
        }
        return mapping.get(state, [])

    # === Checkpoint Manager ===

    def save_checkpoint(
        self, plan_id: str, record: StateRecord, locked: list[int],
        tentative: list[PlanSlot], shadows: list[tuple]
    ) -> Checkpoint:
        """保存 Slot 粒度检查点。

        locked: 已确认不可变更的 Slot 索引列表
        tentative: 当前草案 Slot 列表
        shadows: [(slot_index, alternative_poi_id, prechecked), ...] 预计算替代候选

        Args:
            plan_id: Plan 唯一标识
            record: 当前状态记录（用于 version 和 state）
            locked: 已确认 Slot 索引
            tentative: 草案 Slot 列表
            shadows: 影子候选列表

        Returns:
            保存的 Checkpoint 对象
        """
        cp = Checkpoint(
            plan_id=plan_id,
            version=record.fallback_retry_count + 1,
            state=record.state,
            locked_slots=[LockedSlot(slot_index=i) for i in locked],
            tentative_slots=[
                TentativeSlot(
                    slot_index=s.sequence, poi_id=s.poi.id,
                    start_time=s.time_range.start, end_time=s.time_range.end,
                    action=s.action,
                ) for s in tentative
            ],
            shadow_candidates=[
                ShadowSlot(slot_index=i, alternative_poi_id=p, prechecked=c)
                for i, p, c in shadows
            ],
        )
        self.checkpoints[plan_id] = cp
        return cp

    def get_checkpoint(self, plan_id: str) -> Checkpoint | None:
        """读取 Plan 的最新检查点。

        Args:
            plan_id: Plan 唯一标识

        Returns:
            检查点对象或 None
        """
        return self.checkpoints.get(plan_id)

    def get_locked_indices(self, plan_id: str) -> list[int]:
        """获取已确认不可变更的 Slot 索引。

        Args:
            plan_id: Plan 唯一标识

        Returns:
            已锁定 Slot 索引列表
        """
        cp = self.checkpoints.get(plan_id)
        return [s.slot_index for s in cp.locked_slots] if cp else []

    # === Result Store ===

    def store_result(self, plan_id: str, agent_name: str, result: AgentResult):
        """存储 Agent 执行结果。

        根据 data 内容自动分类：draft → drafts / execution → execution_results。

        Args:
            plan_id: Plan 唯一标识
            agent_name: Agent 名称
            result: Agent 执行结果
        """
        self.agent_results[plan_id][agent_name] = result
        if "draft" in result.data:
            self.drafts[plan_id] = result.data["draft"]
        if "execution" in result.data:
            self.execution_results[plan_id] = result.data["execution"]

    def get_draft(self, plan_id: str) -> PlanDraft | None:
        """获取 Plan 的最新草案。

        Args:
            plan_id: Plan 唯一标识

        Returns:
            PlanDraft 对象或 None
        """
        return self.drafts.get(plan_id)

    def get_execution(self, plan_id: str) -> ExecutionResult | None:
        """获取 Plan 的执行结果。

        Args:
            plan_id: Plan 唯一标识

        Returns:
            ExecutionResult 对象或 None
        """
        return self.execution_results.get(plan_id)
