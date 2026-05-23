"""Planning Engine —— 两阶段求解器：Phase1 CSP + Phase2 LLM。

将候选 POI 池转换为可执行的时间轴方案 (PlanDraft)。

Phase 1: 硬约束过滤（纯代码，≤50ms）
  - 类型偏好匹配评分
  - 预算约束降级
  - 距离 > 20km 直接排除
  - 心情标签匹配加分

Phase 2: 软约束排序（LLM，≤3s）
  - Jinja2 模板渲染 Prompt
  - 调用 LLM
  - 超时降级为 Phase 1 评分降序排序

Shadow 预计算:
  Phase 1 后为每个 Slot 预计算同类型替代候选（shadow_id），
  写入 PlanSlot.shadow_id，供 Fallback Engine 优先使用。

输出: PlanDraft (含 slots, total_cost, confidence, version, shadow_id)

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

from snaptrip_shared.core.constants import (
    PLANNING_PHASE2_TIMEOUT_S,
)
from snaptrip_shared.core.logging import get_logger
from snaptrip_shared.schemas.plan import (
    POI,
    CandidatePool,
    EnrichedIntent,
    IntentSchema,
    PlanDraft,
    PlanSlot,
    TimeRange,
)

from agent_worker.app.agent.ports.llm import LLMPort
from agent_worker.app.agent.ports.prompt import PromptPort
from agent_worker.app.agent.protocol import AgentContext, AgentResult, BaseAgent
from agent_worker.app.agent.skills import build_skill_prompt, match_skills

logger = get_logger(__name__)


class PlanningEngine(BaseAgent):
    name = "planning_engine"

    def __init__(
        self,
        llm: LLMPort | None = None,
        prompt_renderer: PromptPort | None = None,
    ) -> None:
        super().__init__()
        self._llm = llm
        self._prompt_renderer = prompt_renderer

    async def execute(self, context: AgentContext) -> AgentResult:
        """两阶段规划：Phase1 硬约束 → Phase2 LLM 算序 → 时隙生成。

        从 history 提取 CandidatePool 和 EnrichedIntent，执行完整规划流程。

        Args:
            context: 含上游 Agent 结果的上下文

        Returns:
            AgentResult.data["draft"] = PlanDraft
        """
        logger.info("planning_engine_started", plan_id=context.plan_id, user_id=context.user_id)
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

        matched_skills = match_skills(
            scene_type=intent.scene_type,
            type_prefs=intent.type_prefs,
        )
        skill_prompt = build_skill_prompt(matched_skills)

        try:
            ranked = await asyncio.wait_for(
                self._phase2_llm_sort(candidates, intent, start_time, end_time, skill_prompt, context.lat, context.lng),
                timeout=PLANNING_PHASE2_TIMEOUT_S,
            )
        except TimeoutError:
            logger.info("planning_engine_phase2_timeout", plan_id=context.plan_id)
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
        logger.info("planning_engine_completed", plan_id=context.plan_id, slot_count=len(slots))
        return AgentResult(data={"draft": draft.model_dump()})

    def _phase1_hard_filter(
        self, candidates: list[POI], intent: IntentSchema, lat: float, lng: float, start: datetime, end: datetime
    ) -> list[POI]:
        """Phase 1: 硬约束过滤（纯代码，≤50ms）。

        按类型偏好、预算、距离（>20km 直接排除）、心情标签评分排序。

        Args:
            candidates: 候选 POI 列表
            intent: 用户意图
            lat/lng: 参考坐标
            start/end: 时间窗口（预留，当前未使用）

        Returns:
            ≤10 个按评分降序的 POI
        """
        from agent_worker.app.agent.engines.retrieval_engine import haversine

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

    async def _phase2_llm_sort(
        self,
        candidates: list[POI],
        intent: IntentSchema,
        start: datetime,
        end: datetime,
        skill_prompt: str = "",
        lat: float = 0.0,
        lng: float = 0.0,
    ) -> list[POI]:
        try:
            from agent_worker.app.agent.engines.retrieval_engine import haversine

            enriched = []
            for p in candidates:
                d = p.model_dump()
                d["distance_km"] = round(haversine(lat, lng, p.lat, p.lng), 1)
                enriched.append(d)

            prompt = await self._get_prompt_renderer().render(
                "planning.j2",
                {
                    "scene_type": intent.scene_type,
                    "guest_count": intent.guest_count,
                    "budget": intent.budget,
                    "mood_prefs": intent.mood_prefs or [],
                    "type_prefs": intent.type_prefs or [],
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "candidates": enriched,
                    "skill_prompt": skill_prompt,
                },
            )
            from snaptrip_shared.core.config import settings

            parsed = await self._get_llm().chat_json(
                prompt=prompt,
                model_alias=settings.LLM_DEFAULT_MODEL,
                timeout_s=PLANNING_PHASE2_TIMEOUT_S,
                temperature=0.5,
                max_tokens=1024,
            )
        except Exception:
            logger.warning("planning_engine_phase2_failed", exc_info=True)
            return self._phase2_fallback_sort(candidates, intent)

        poi_map = {p.id: p for p in candidates}
        result = []
        for item in parsed.get("slots", []):
            pid = item.get("poi_id")
            if pid and pid in poi_map:
                result.append(poi_map[pid])
        return result or self._phase2_fallback_sort(candidates, intent)

    def _phase2_fallback_sort(self, candidates: list[POI], intent: IntentSchema) -> list[POI]:
        """Phase 2 降级排序（纯代码，LLM 超时时使用）。

        按评分 + 心情标签匹配加权排序。

        Args:
            candidates: Phase 1 输出的候选 POI
            intent: 用户意图

        Returns:
            排序后的 POI 列表
        """
        scored = []
        for p in candidates:
            s = p.rating * 2
            if intent.mood_prefs:
                s += len(set(p.mood_tags) & set(intent.mood_prefs)) * 3
            scored.append((p, s))
        scored.sort(key=lambda x: -x[1])
        return [p for p, _ in scored]

    def _generate_slots(self, pois: list[POI], start: datetime, end: datetime) -> list[PlanSlot]:
        """根据排序后的 POI 列表生成时间轴 Slots。

        最多 4 个 Slot，均匀分配时间窗口，含移动时间随机扰动。
        同时为每个 Slot 预计算同类型 Shadow Candidate（shadow_id）。

        Args:
            pois: 排序后的 POI 列表
            start: 计划开始时间
            end: 计划结束时间

        Returns:
            PlanSlot 列表（≤4 个）
        """
        slots = []
        total_min = (end - start).total_seconds() / 60
        cnt = min(len(pois), 4)
        dur = total_min / max(cnt, 1)
        cur = start
        action_map = {"restaurant": "book_table", "cafe": "arrive", "attraction": "arrive", "activity": "book_ticket"}

        shadow_pool = [p for p in pois]
        for i, poi in enumerate(pois[:cnt]):
            move = random.randint(10, 25) if i > 0 else 0
            cur += timedelta(minutes=move)
            slot_end = cur + timedelta(minutes=min(dur, 90))

            shadow_id = None
            shadows = [p for p in shadow_pool if p.type == poi.type and p.id != poi.id]
            if shadows:
                shadow_id = random.choice(shadows).id

            slots.append(
                PlanSlot(
                    sequence=i,
                    poi=poi,
                    time_range=TimeRange(start=cur, end=slot_end),
                    action=action_map.get(poi.type, "arrive"),
                    estimated_cost=poi.avg_price,
                    move_time_min=move,
                    confidence=0.7,
                    shadow_id=shadow_id,
                )
            )
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

    def _get_llm(self) -> LLMPort:
        if self._llm is None:
            from agent_worker.app.agent.adapters.llm import LLMAdapter

            self._llm = LLMAdapter()
        return self._llm

    def _get_prompt_renderer(self) -> PromptPort:
        if self._prompt_renderer is None:
            from agent_worker.app.agent.adapters.prompt import JinjaPromptAdapter

            self._prompt_renderer = JinjaPromptAdapter()
        return self._prompt_renderer
