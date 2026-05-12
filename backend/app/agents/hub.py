"""Master Controller — 中央控制器：State Registry + Policy Engine + Checkpoint Manager"""

from __future__ import annotations

from pydantic import BaseModel

from app.agents.protocol import AgentContext, AgentResult
from app.core.constants import FALLBACK_MAX_RETRY, PlanStatus
from app.core.state import PlanStateMachine, StateEvent, StateRecord
from app.schemas.checkpoint import Checkpoint, LockedSlot, ShadowSlot, TentativeSlot
from app.schemas.plan import ExecutionResult, PlanDraft, PlanSlot


class PolicyDecision(BaseModel):
    next_state: str
    agents_to_activate: list[str]
    message: str = ""


class MasterController:

    def __init__(self):
        self.state_machine = PlanStateMachine()
        self.checkpoints: dict[str, Checkpoint] = {}
        self.agent_results: dict[str, dict[str, AgentResult]] = {}
        self.drafts: dict[str, PlanDraft] = {}
        self.execution_results: dict[str, ExecutionResult] = {}

    # === State Registry ===

    def init_plan(self, plan_id: str, context: AgentContext) -> StateRecord:
        record = self.state_machine.get_or_create(plan_id)
        payload = {"user_input": context.user_input, "lat": context.lat, "lng": context.lng}
        self.state_machine.transition(record, StateEvent.CREATE_REQUEST, payload)
        context.state = record.state
        context.plan_id = plan_id
        self.agent_results[plan_id] = {}
        return record

    def get_state(self, plan_id: str) -> StateRecord:
        return self.state_machine.get_or_create(plan_id)

    # === Policy Engine ===

    def decide(self, record: StateRecord, event: StateEvent, payload: dict | None = None) -> PolicyDecision:
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
        if result.status == "full_success":
            return self.decide(record, StateEvent.EXECUTION_SUCCESS)
        elif result.status == "partial_success":
            record.fallback_retry_count += 1
            if record.fallback_retry_count < FALLBACK_MAX_RETRY:
                return self.decide(record, StateEvent.EXECUTION_PARTIAL_FAIL)
        return PolicyDecision(next_state=PlanStatus.FAILED, agents_to_activate=[])

    def _agents_for_state(self, state: str) -> list[str]:
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
        return self.checkpoints.get(plan_id)

    def get_locked_indices(self, plan_id: str) -> list[int]:
        cp = self.checkpoints.get(plan_id)
        return [s.slot_index for s in cp.locked_slots] if cp else []

    # === Result Store ===

    def store_result(self, plan_id: str, agent_name: str, result: AgentResult):
        self.agent_results[plan_id][agent_name] = result
        if "draft" in result.data:
            self.drafts[plan_id] = result.data["draft"]
        if "execution" in result.data:
            self.execution_results[plan_id] = result.data["execution"]

    def get_draft(self, plan_id: str) -> PlanDraft | None:
        return self.drafts.get(plan_id)

    def get_execution(self, plan_id: str) -> ExecutionResult | None:
        return self.execution_results.get(plan_id)
