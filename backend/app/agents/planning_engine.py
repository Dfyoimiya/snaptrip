"""Planning Engine — 两阶段求解器：Phase1 CSP + Phase2 LLM"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.core.constants import (
    PLANNING_PHASE2_TIMEOUT_S,
)
from app.schemas.plan import (
    POI,
    CandidatePool,
    EnrichedIntent,
    IntentSchema,
    PlanDraft,
    PlanSlot,
    TimeRange,
)


class PlanningEngine(BaseAgent):
    name = "planning_engine"

    async def execute(self, context: AgentContext) -> AgentResult:
        enriched = self._extract_enriched(context)
        pool = self._extract_pool(context)
        intent = enriched.intent if enriched else IntentSchema()

        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = start_time + timedelta(hours=4)

        if intent.time_window:
            start_time = intent.time_window.start
            end_time = intent.time_window.end

        candidates = self._phase1_hard_filter(pool.candidates, intent, context.lat, context.lng, start_time, end_time)

        try:
            ranked = await asyncio.wait_for(
                self._phase2_llm_sort(candidates, intent, start_time, end_time),
                timeout=PLANNING_PHASE2_TIMEOUT_S,
            )
        except TimeoutError:
            ranked = self._phase2_fallback_sort(candidates, intent)

        slots = self._generate_slots(ranked, start_time, end_time)

        total_cost = sum(s.estimated_cost for s in slots)
        total_time = int((end_time - start_time).total_seconds() / 60)

        draft = PlanDraft(
            plan_id=context.plan_id,
            slots=slots,
            total_cost=total_cost,
            total_time_min=total_time,
            confidence=0.7,
            version=1,
        )
        return AgentResult(data={"draft": draft.model_dump()})

    def _phase1_hard_filter(self, candidates: list[POI], intent: IntentSchema,
                            lat: float, lng: float, start: datetime, end: datetime) -> list[POI]:
        from app.agents.retrieval_engine import haversine
        filtered = []
        for poi in candidates:
            score = 0.0
            if intent.type_prefs and poi.type not in intent.type_prefs:
                score -= 5
            if intent.budget and poi.avg_price > intent.budget * 0.7:
                score -= 3
            dist = haversine(lat, lng, poi.lat, poi.lng)
            score += max(0, 5 - dist)
            if intent.mood_prefs:
                matches = len(set(poi.mood_tags) & set(intent.mood_prefs))
                score += matches * 2
            filtered.append((poi, score))
        filtered.sort(key=lambda x: -x[1])
        return [p for p, _ in filtered[:10]]

    async def _phase2_llm_sort(self, candidates: list[POI], intent: IntentSchema,
                                start: datetime, end: datetime) -> list[POI]:
        try:
            from jinja2 import Template
            with open("app/agents/prompts/planning.j2") as f:
                tpl = Template(f.read())

            from app.agents.retrieval_engine import haversine
            enriched = []
            for p in candidates:
                d = p.model_dump()
                d["distance_km"] = round(haversine(39.9, 116.4, p.lat, p.lng), 1)
                enriched.append(d)

            prompt = tpl.render(
                scene_type=intent.scene_type, guest_count=intent.guest_count,
                budget=intent.budget, mood_prefs=intent.mood_prefs or [],
                type_prefs=intent.type_prefs or [], start_time=start.isoformat(),
                end_time=end.isoformat(), candidates=enriched,
            )

            import json

            import httpx
            async with httpx.AsyncClient(timeout=PLANNING_PHASE2_TIMEOUT_S) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": "Bearer placeholder", "Content-Type": "application/json"},
                    json={"model": "deepseek/deepseek-v3", "messages": [{"role": "user", "content": prompt}],
                          "temperature": 0.5, "max_tokens": 1024},
                )
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content.strip().removeprefix("```json").removesuffix("```"))
        except Exception:
            return self._phase2_fallback_sort(candidates, intent)

        poi_map = {p.id: p for p in candidates}
        result = []
        for item in parsed.get("slots", []):
            pid = item.get("poi_id")
            if pid and pid in poi_map:
                result.append(poi_map[pid])
        return result or self._phase2_fallback_sort(candidates, intent)

    def _phase2_fallback_sort(self, candidates: list[POI], intent: IntentSchema) -> list[POI]:
        scored = []
        for p in candidates:
            s = p.rating * 2
            if intent.mood_prefs:
                s += len(set(p.mood_tags) & set(intent.mood_prefs)) * 3
            scored.append((p, s))
        scored.sort(key=lambda x: -x[1])
        return [p for p, _ in scored]

    def _generate_slots(self, pois: list[POI], start: datetime, end: datetime) -> list[PlanSlot]:
        slots = []
        total_min = (end - start).total_seconds() / 60
        cnt = min(len(pois), 4)
        dur = total_min / max(cnt, 1)
        cur = start
        action_map = {"restaurant": "book_table", "cafe": "arrive",
                      "attraction": "arrive", "activity": "book_ticket"}

        shadow_pool = [p for p in pois]
        for i, poi in enumerate(pois[:cnt]):
            move = random.randint(10, 25) if i > 0 else 0
            cur += timedelta(minutes=move)
            slot_end = cur + timedelta(minutes=min(dur, 90))

            shadow_id = None
            shadows = [p for p in shadow_pool if p.type == poi.type and p.id != poi.id]
            if shadows:
                shadow_id = random.choice(shadows).id

            slots.append(PlanSlot(
                sequence=i, poi=poi,
                time_range=TimeRange(start=cur, end=slot_end),
                action=action_map.get(poi.type, "arrive"),
                estimated_cost=poi.avg_price, move_time_min=move, confidence=0.7,
                shadow_id=shadow_id,
            ))
            cur = slot_end
            if cur >= end:
                break
        return slots

    def _extract_enriched(self, context) -> EnrichedIntent | None:
        for h in reversed(context.history):
            if "enriched_intent" in h.data:
                d = h.data["enriched_intent"]
                return EnrichedIntent(**d)
        return None

    def _extract_pool(self, context) -> CandidatePool:
        for h in reversed(context.history):
            if "candidate_pool" in h.data:
                return CandidatePool(**h.data["candidate_pool"])
        return CandidatePool()
