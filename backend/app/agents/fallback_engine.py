"""Fallback Engine — Shadow Candidate 查找 + 局部重检索 + 涟漪重排"""

from __future__ import annotations

import random
from datetime import timedelta

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.schemas.plan import (
    POI,
    EnrichedIntent,
    ExecutionResult,
    PlanDraft,
    PlanSlot,
    RevisedPlan,
    SlotDiff,
    TimeRange,
)


class FallbackEngine(BaseAgent):
    name = "fallback_engine"

    async def execute(self, context: AgentContext) -> AgentResult:
        execution_result = self._extract_execution(context)
        draft = self._extract_draft(context)
        enriched = self._extract_enriched(context)

        if not execution_result or not draft:
            return AgentResult(status="failed", error="Missing execution result or draft")

        revised = await self._repair(draft, execution_result, enriched)

        return AgentResult(data={"revised_plan": revised.model_dump()})

    async def _repair(self, draft: PlanDraft, result: ExecutionResult,
                      enriched: EnrichedIntent | None) -> RevisedPlan:
        diffs = []
        new_slots = list(draft.slots)

        for failed in result.failed_slots:
            shadow = failed.shadow_candidate
            if shadow and shadow.prechecked:
                alt_poi = self._find_alternative(draft, failed.slot_index)
            else:
                alt_poi = self._retrieve_alternative(draft, failed.slot_index, enriched)

            if alt_poi:
                old = new_slots[failed.slot_index]
                new_slots[failed.slot_index] = PlanSlot(
                    sequence=failed.slot_index,
                    poi=alt_poi,
                    time_range=old.time_range,
                    action=old.action,
                    estimated_cost=alt_poi.avg_price,
                    move_time_min=old.move_time_min,
                    confidence=0.6,
                )
                diffs.append(SlotDiff(
                    slot_index=failed.slot_index,
                    old_poi_id=old.poi.id, new_poi_id=alt_poi.id,
                    old_poi_name=old.poi.name, new_poi_name=alt_poi.name,
                ))
                self._ripple_reschedule(new_slots, failed.slot_index)

        revised = PlanDraft(
            plan_id=draft.plan_id, slots=new_slots,
            total_cost=sum(s.estimated_cost for s in new_slots),
            total_time_min=draft.total_time_min,
            confidence=0.5, version=draft.version + 1,
        )
        return RevisedPlan(plan=revised, diff_patch=diffs)

    def _find_alternative(self, draft: PlanDraft, slot_index: int) -> POI | None:
        from app.data.seed_pois import SEED_POIS
        original = draft.slots[slot_index]

        if original.shadow_id:
            shadow = next((p for p in SEED_POIS if p.id == original.shadow_id), None)
            if shadow:
                return POI(**shadow.model_dump())

        candidates = [p for p in SEED_POIS
                      if p.type == original.poi.type and p.id != original.poi.id]
        return random.choice(candidates) if candidates else None

    def _retrieve_alternative(self, draft: PlanDraft, slot_index: int,
                              enriched: EnrichedIntent | None) -> POI | None:
        return self._find_alternative(draft, slot_index)

    def _ripple_reschedule(self, slots: list[PlanSlot], changed_idx: int):
        for i in range(changed_idx + 1, len(slots)):
            prev = slots[i - 1]
            cur = slots[i]
            earliest = prev.time_range.end + timedelta(minutes=prev.move_time_min)
            if earliest > cur.time_range.start:
                delta = (earliest - cur.time_range.start).total_seconds() / 60
                cur.time_range = TimeRange(
                    start=earliest,
                    end=cur.time_range.end + timedelta(minutes=delta),
                )

    def _extract_execution(self, context) -> ExecutionResult | None:
        for h in reversed(context.history):
            if "execution" in h.data:
                return ExecutionResult(**h.data["execution"])
        return None

    def _extract_draft(self, context) -> PlanDraft | None:
        for h in reversed(context.history):
            if "draft" in h.data:
                return PlanDraft(**h.data["draft"])
        return None

    def _extract_enriched(self, context) -> EnrichedIntent | None:
        for h in reversed(context.history):
            if "enriched_intent" in h.data:
                return EnrichedIntent(**h.data["enriched_intent"])
        return None
