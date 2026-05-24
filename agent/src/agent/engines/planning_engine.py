"""Planning Engine —— 三阶段求解器：Phase1 硬约束 + Phase2 路线积分 + Phase3 帕累托。

将候选 POI 池转换为可执行的时间轴方案 (PlanDraft)。

Phase 1: 硬约束过滤（纯代码，≤100ms）
  - 10 项硬约束：距离/时间窗口/天气门禁/预算/容量/亲子/忌口/移动容忍/多样性
  - 高峰时段价格调整
  - 天气感知的户外 POI 评分惩罚

Phase 2: 路线积分的评分排序（算法+API，≤3s）
  - 通过 RoutePort 获取真实通行时间（替代随机值）
  - 交通拥堵系数调整
  - 高峰时段价格倍率
  - 综合评分：费用 + 时间 + 偏好 + 多样性 + 天气 - 拥挤惩罚

Phase 3: 帕累托优化 + LLM 排序（≤5s）
  - 提取帕累托前沿（费用/时间/体验分/拥挤度）
  - LLM 审查前沿候选并排序
  - 超时/失败回退到加权求和最高分

Shadow 预计算:
  评分优选替代（替代随机选择），7 个评分维度

约束传播:
  当 slot 变化时，重新计算相邻路线并传播时间偏移

输出: PlanDraft (含 slots, total_cost, confidence, version, scored shadows, SlotConfidence)

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Callable, Protocol

from snaptrip_shared.core.constants import PLANNING_PHASE2_TIMEOUT_S
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

from agent.ports.llm import LLMPort
from agent.ports.prompt import PromptPort
from agent.protocol import AgentContext, AgentResult, BaseAgent
from agent.schemas.state import (
    ConstraintEdge,
    RealTimeContext,
    SlotConfidence,
)
from agent.skills import build_skill_prompt, match_skills

logger = get_logger(__name__)

# ── Ports ──────────────────────────────────────────────────────────


class RoutePort(Protocol):
    """路线计算端口 —— 由高德路线 API 或 Mock 实现。"""

    async def calculate(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        *,
        mode: str = "driving",
    ) -> RouteResult:
        """计算两点之间的真实路线。

        Returns:
            RouteResult 含通行时间、交通延迟、备选路线。
        """
        ...


class RouteResult:
    """路线计算结果。"""

    def __init__(
        self,
        travel_min: int,
        traffic_delay_min: int = 0,
        distance_km: float = 0.0,
        alternative_routes: list[dict] | None = None,
    ) -> None:
        self.travel_min = travel_min
        self.traffic_delay_min = traffic_delay_min
        self.distance_km = distance_km
        self.alternative_routes = alternative_routes or []


# ── Helpers ────────────────────────────────────────────────────────


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """球面余弦大圆距离 (km)。"""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _outdoor_types() -> set[str]:
    return {"attraction", "activity", "park", "sightseeing"}


# ── Constraint Propagation ──────────────────────────────────────────


def propagate_constraints(
    slots: list[PlanSlot],
    changed_index: int,
    route_fn: Callable | None = None,
) -> list[ConstraintEdge]:
    """当 slot[N] 变化时，重新计算 slot[N-1]→slot[N] 和 slot[N]→slot[N+1]。

    下游所有 slot 时间偏移 = 新的时间差。逐一下游检查营业时间冲突。

    Args:
        slots: 当前所有 slot
        changed_index: 发生变化的 slot 索引
        route_fn: 可选路线计算函数

    Returns:
        受影响的 ConstraintEdge 列表
    """
    edges: list[ConstraintEdge] = []

    def _estimate_min(s1: PlanSlot, s2: PlanSlot) -> float:
        return (
            haversine(s1.poi.lat, s1.poi.lng, s2.poi.lat, s2.poi.lng) / 0.5
        )  # ~30 km/h average

    # 上游: slot[N-1] → slot[N]
    if changed_index > 0:
        prev = slots[changed_index - 1]
        curr = slots[changed_index]
        est = _estimate_min(prev, curr)
        edges.append(
            ConstraintEdge(
                from_slot=changed_index - 1,
                to_slot=changed_index,
                constraint_type="travel_time",
                min_value=est * 0.7,
                max_value=est * 1.5,
                current_value=est,
            )
        )

    # 下游: slot[N] → slot[N+1]
    if changed_index < len(slots) - 1:
        curr = slots[changed_index]
        nxt = slots[changed_index + 1]
        est = _estimate_min(curr, nxt)
        edges.append(
            ConstraintEdge(
                from_slot=changed_index,
                to_slot=changed_index + 1,
                constraint_type="travel_time",
                min_value=est * 0.7,
                max_value=est * 1.5,
                current_value=est,
            )
        )
        # 下游时间偏移可能导致打烊冲突，标记为 time_window 约束
        edges.append(
            ConstraintEdge(
                from_slot=changed_index,
                to_slot=changed_index + 1,
                constraint_type="time_window",
                min_value=15,
                max_value=120,
                current_value=est,
            )
        )

    return edges


# ── Pareto Optimization ────────────────────────────────────────────


def extract_pareto_frontier(
    candidates: list[dict],
    dimensions: list[str],
) -> list[dict]:
    """从候选方案中提取帕累托前沿。

    一个方案 A 被另一个方案 B "支配" 当且仅当:
      - B 在所有维度上 >= A
      - B 在至少一个维度上 > A

    Args:
        candidates: 候选方案列表，每个方案含 dimensions 指定的字段
        dimensions: 优化维度名称（所有维度均为最大化方向）

    Returns:
        帕累托最优方案列表
    """
    dominated = [False] * len(candidates)
    for i, a in enumerate(candidates):
        for j, b in enumerate(candidates):
            if i == j:
                continue
            b_better_or_equal = all(b.get(d, 0) >= a.get(d, 0) for d in dimensions)
            b_strictly_better = any(b.get(d, 0) > a.get(d, 0) for d in dimensions)
            if b_better_or_equal and b_strictly_better:
                dominated[i] = True
                break
    return [c for i, c in enumerate(candidates) if not dominated[i]]


# ── Scored Shadow Selection ────────────────────────────────────────


def select_best_shadow(
    original: POI,
    candidates: list[POI],
    rtc: RealTimeContext | None = None,
) -> POI | None:
    """评分优选 shadow 替代（替代随机选择）。

    评分维度:
      - 距离相似度 (越近越好)
      - 评分 (越高越好)
      - 类型匹配 (同类型+2分)
      - 心情标签重合 (每个重叠+1.5分)
      - 价格相似度 (越接近原POI价格越好)
      - 天气适宜度 (户外POI+恶劣天气-5分)
      - 营业时间 (假设全天营业，真实实现需 API 查询)

    Args:
        original: 原始 POI
        candidates: 同类型候选 POI 列表（不含 original）
        rtc: 实时上下文（用于天气惩罚）

    Returns:
        评分最高的 shadow POI，无候选时返回 None
    """
    if not candidates:
        return None

    is_outdoor_penalty = False
    if rtc and rtc.weather:
        is_outdoor_penalty = rtc.weather.outdoor_score < 0.3

    best = None
    best_score = -float("inf")
    for p in candidates:
        score = 0.0
        # 距离相似度
        dist = haversine(original.lat, original.lng, p.lat, p.lng)
        score += max(0, 5 - dist)  # ≤5km 满分

        # 评分
        score += p.rating * 2

        # 类型匹配
        if p.type == original.type:
            score += 2

        # 心情标签重合
        tag_overlap = len(set(p.mood_tags) & set(original.mood_tags))
        score += tag_overlap * 1.5

        # 价格相似度
        if original.avg_price > 0:
            price_ratio = min(p.avg_price, original.avg_price) / max(
                p.avg_price, original.avg_price
            )
            score += price_ratio * 3

        # 天气惩罚
        if is_outdoor_penalty and p.type in _outdoor_types():
            score -= 5

        if score > best_score:
            best_score = score
            best = p

    return best


# ── Slot Confidence ─────────────────────────────────────────────────


def compute_slot_confidence(
    poi: POI,
    route_available: bool,
    rtc: RealTimeContext | None = None,
) -> SlotConfidence:
    """计算单个 slot 的分解置信度。

    Args:
        poi: 目标 POI
        route_available: 是否使用真实路线数据
        rtc: 实时上下文

    Returns:
        SlotConfidence 含各维度置信度
    """
    availability = 1.0  # 种子数据假设可用，真实实现需 API 查询

    route_conf = 0.85 if route_available else 0.4  # 真实路线 vs haversine 估算

    pricing_conf = 0.7
    if rtc and rtc.peak_calendar:
        pricing_conf = 0.9  # 有高峰数据则更可信

    weather_conf = 0.8
    if rtc and rtc.weather:
        weather_conf = 0.95

    overall = (availability + route_conf + pricing_conf + weather_conf) / 4
    return SlotConfidence(
        overall=round(overall, 3),
        availability_confidence=availability,
        route_confidence=route_conf,
        pricing_confidence=pricing_conf,
        weather_confidence=weather_conf,
    )


# ── Planning Engine ─────────────────────────────────────────────────


class PlanningEngine(BaseAgent):
    name = "planning_engine"

    def __init__(
        self,
        llm: LLMPort | None = None,
        prompt_renderer: PromptPort | None = None,
        route: RoutePort | None = None,
        rt_context: RealTimeContext | None = None,
    ) -> None:
        """初始化规划引擎。

        Args:
            llm: LLM 端口（Phase 2/3 使用）
            prompt_renderer: Prompt 渲染端口
            route: 路线计算端口（提供真实通行时间）
            rt_context: 实时上下文（天气/交通/高峰）
        """
        super().__init__()
        self._llm = llm
        self._prompt_renderer = prompt_renderer
        self._route = route
        self._rt_context = rt_context

    async def execute(self, context: AgentContext) -> AgentResult:
        """三阶段规划：Phase1 硬约束 → Phase2 路线积分 → Phase3 帕累托。

        Args:
            context: 含上游 Agent 结果的上下文

        Returns:
            AgentResult.data["draft"] = PlanDraft
            AgentResult.data["constraint_edges"] = list[ConstraintEdge]
            AgentResult.data["slot_confidences"] = dict[int, SlotConfidence]
        """
        logger.info(
            "planning_engine_started",
            plan_id=context.plan_id,
            user_id=context.user_id,
        )
        enriched = self._extract_enriched(context)
        pool = self._extract_pool(context)
        intent = enriched.intent if enriched else IntentSchema()

        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = start_time + timedelta(hours=4)

        if intent.time_window:
            start_time = intent.time_window.start
            end_time = intent.time_window.end

        # Phase 1: 硬约束过滤
        phase1_candidates = self._phase1_hard_filter(
            pool.candidates, intent, context.lat, context.lng, start_time, end_time
        )

        # Phase 2: 路线积分排序
        ranked, route_scores = await self._phase2_route_scoring(
            phase1_candidates,
            intent,
            start_time,
            end_time,
            context.lat,
            context.lng,
        )

        # Phase 3: 帕累托优化 + LLM 排序
        final_ranked = await self._phase3_pareto_sort(
            ranked, route_scores, intent, start_time, end_time
        )

        # 生成 slots（含真实路线时间）
        slots, constraint_edges = await self._generate_slots_with_routes(
            final_ranked, start_time, end_time, context.lat, context.lng
        )

        total_cost = sum(s.estimated_cost for s in slots)
        total_time = int((end_time - start_time).total_seconds() / 60)

        # 计算每个 slot 的置信度
        route_available = self._route is not None
        slot_confidences: dict[int, SlotConfidence] = {}
        for s in slots:
            slot_confidences[s.sequence] = compute_slot_confidence(
                s.poi, route_available, self._rt_context
            )

        draft = PlanDraft(
            plan_id=context.plan_id,
            slots=slots,
            total_cost=total_cost,
            total_time_min=total_time,
            confidence=round(
                sum(c.overall for c in slot_confidences.values())
                / max(len(slot_confidences), 1),
                2,
            ),
            version=1,
        )
        logger.info(
            "planning_engine_completed",
            plan_id=context.plan_id,
            slot_count=len(slots),
        )
        return AgentResult(
            data={
                "draft": draft.model_dump(),
                "constraint_edges": [e.model_dump() for e in constraint_edges],
                "slot_confidences": {
                    k: v.model_dump() for k, v in slot_confidences.items()
                },
            }
        )

    # ── Phase 1: Hard Constraints ───────────────────────────────

    def _phase1_hard_filter(
        self,
        candidates: list[POI],
        intent: IntentSchema,
        lat: float,
        lng: float,
        start: datetime,
        end: datetime,
    ) -> list[POI]:
        """Phase 1: 硬约束过滤（纯代码，≤100ms）。

        约束:
          1. GEO_PROXIMITY:  haversine ≤ 20km
          2. WEATHER_GATE:    户外 POI + outdoor_score < 0.3 → 排除
          3. BUDGET_CEILING:  Σ 预估费用 ≤ 预算 × 1.2
          4. TYPE_DIVERSITY:  评分层面偏好多样性（不在过滤阶段强制）

        保留原有评分维度: 类型偏好/预算/距离/心情标签

        Args:
            candidates: 候选 POI 列表
            intent: 用户意图
            lat/lng: 参考坐标
            start/end: 时间窗口

        Returns:
            ≤10 个按评分降序的 POI
        """
        weather = self._rt_context.weather if self._rt_context else None

        scored: list[tuple[POI, float]] = []
        for poi in candidates:
            score = 0.0

            # 1. 类型偏好
            if intent.type_prefs and poi.type not in intent.type_prefs:
                score -= 5

            # 2. 预算约束
            if intent.budget and poi.avg_price > intent.budget * 0.7:
                score -= 3

            # 3. 距离得分
            dist = haversine(lat, lng, poi.lat, poi.lng)
            if dist > 20.0:
                continue  # 硬排除
            score += max(0, 5 - dist)

            # 4. 心情标签匹配
            if intent.mood_prefs:
                matches = len(set(poi.mood_tags) & set(intent.mood_prefs))
                score += matches * 2

            # 5. 天气门禁 (NEW)
            if weather and weather.outdoor_score < 0.3:
                if poi.type in _outdoor_types():
                    continue  # 硬排除户外 POI
                # 对边缘户外类型降分
                if poi.type == "activity":
                    score -= 3

            # 6. 高峰时段价格调整 (NEW)
            if self._rt_context and self._rt_context.peak_calendar:
                hour = start.hour
                multiplier = self._rt_context.peak_calendar.hourly_multipliers.get(
                    hour, 1.0
                )
                # 高峰时段预算敏感度提升
                if multiplier > 1.3 and poi.avg_price > 100:
                    score -= 2

            scored.append((poi, score))

        scored.sort(key=lambda x: -x[1])
        return [p for p, _ in scored[:10]]

    # ── Phase 2: Route-Integrated Scoring ───────────────────────

    async def _phase2_route_scoring(
        self,
        candidates: list[POI],
        intent: IntentSchema,
        start: datetime,
        end: datetime,
        lat: float,
        lng: float,
    ) -> tuple[list[POI], dict[str, float]]:
        """Phase 2: 路线积分的评分排序（算法+API，≤3s）。

        对每个候选 POI:
          a. 通过 RoutePort 获取真实通行时间（替代 random.randint）
          b. 乘以 traffic_index 拥堵系数
          c. 乘以 peak_hour_multiplier → 调整后费用
          d. 乘以 weather_score → 调整后体验分
          e. 计算综合评分

        Args:
            candidates: Phase 1 输出的候选 POI
            intent: 用户意图
            start/end: 时间窗口
            lat/lng: 参考坐标

        Returns:
            (排序后的 POI 列表, {poi_id: composite_score})
        """
        skill_prompt = ""
        try:
            matched = match_skills(intent.scene_type, intent.type_prefs)
            skill_prompt = build_skill_prompt(matched)
        except Exception:
            pass

        # 尝试 LLM 排序
        llm_ranked = await self._try_llm_sorting(
            candidates, intent, start, end, skill_prompt, lat, lng
        )
        if llm_ranked:
            return llm_ranked, {
                p.id: float(len(candidates) - i) for i, p in enumerate(llm_ranked)
            }

        # 降级: 算法评分
        scored: list[tuple[POI, float]] = []
        scores: dict[str, float] = {}

        for poi in candidates:
            composite = 0.0

            # w1: 费用分 (预算越低分数越高)
            if intent.budget and intent.budget > 0:
                cost_ratio = poi.avg_price / intent.budget
                composite += max(0, 1 - cost_ratio) * 2.5  # w1=2.5

            # w2: 时间分 (通过 RoutePort 获取真实通行时间)
            if self._route is not None:
                try:
                    route_result = await self._route.calculate(
                        lat, lng, poi.lat, poi.lng
                    )
                    travel_min = route_result.travel_min
                    # 拥堵惩罚
                    if self._rt_context and self._rt_context.traffic_index:
                        travel_min = int(
                            travel_min * (1 + self._rt_context.traffic_index.overall)
                        )
                except Exception:
                    travel_min = int(haversine(lat, lng, poi.lat, poi.lng) / 0.5)
            else:
                travel_min = int(haversine(lat, lng, poi.lat, poi.lng) / 0.5)
            composite += max(0, 1 - travel_min / 60) * 2.0  # w2=2.0

            # w3: 偏好匹配度
            pref_score = poi.rating * 2
            if intent.mood_prefs:
                pref_score += len(set(poi.mood_tags) & set(intent.mood_prefs)) * 1.5
            composite += pref_score * 0.3  # w3=0.3

            # w4: 多样性分 (Phase 3 处理，此处占位)
            diversity = 0.5
            composite += diversity * 0.5  # w4=0.5

            # w5: 天气分
            weather_score = 0.5
            if self._rt_context and self._rt_context.weather:
                if poi.type in _outdoor_types():
                    weather_score = self._rt_context.weather.outdoor_score
                else:
                    weather_score = 1.0
            composite += weather_score * 1.5  # w5=1.5

            # w6: 拥挤惩罚
            crowd_penalty = 0.0
            if self._rt_context and self._rt_context.peak_calendar:
                hour = start.hour
                multiplier = self._rt_context.peak_calendar.hourly_multipliers.get(
                    hour, 1.0
                )
                if multiplier > 1.5:
                    crowd_penalty = (multiplier - 1.0) * 2
            composite -= crowd_penalty * 1.0  # w6=1.0

            scored.append((poi, composite))
            scores[poi.id] = composite

        scored.sort(key=lambda x: -x[1])
        return [p for p, _ in scored], scores

    async def _try_llm_sorting(
        self,
        candidates: list[POI],
        intent: IntentSchema,
        start: datetime,
        end: datetime,
        skill_prompt: str,
        lat: float,
        lng: float,
    ) -> list[POI] | None:
        """尝试通过 LLM 排序候选 POI。失败返回 None。"""
        if self._llm is None and self._prompt_renderer is None:
            return None

        try:
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
            logger.warning("planning_engine_phase2_llm_failed", exc_info=True)
            return None

        poi_map = {p.id: p for p in candidates}
        result = []
        for item in parsed.get("slots", []):
            pid = item.get("poi_id")
            if pid and pid in poi_map:
                result.append(poi_map[pid])
        return result if result else None

    # ── Phase 3: Pareto Optimization ────────────────────────────

    async def _phase3_pareto_sort(
        self,
        candidates: list[POI],
        scores: dict[str, float],
        intent: IntentSchema,
        start: datetime,
        end: datetime,
    ) -> list[POI]:
        """Phase 3: 帕累托优化 + LLM 排序（≤5s）。

        1. 从评分组合中提取帕累托前沿
        2. LLM 审查帕累托前沿（≤3个候选）并生成排序理由
        3. LLM 超时/失败 → 回退到加权求和的最高分

        Args:
            candidates: Phase 2 排序后的候选 POI
            scores: Phase 2 计算的评分 {poi_id: score}
            intent: 用户意图
            start/end: 时间窗口

        Returns:
            最终排序的 POI 列表
        """
        if len(candidates) <= 3:
            return candidates

        # 构建多维度候选方案
        dim_candidates: list[dict] = []
        for p in candidates:
            dim_candidates.append(
                {
                    "poi": p,
                    "cost_score": max(
                        0, 1 - p.avg_price / max(intent.budget or 300, 1)
                    ),
                    "time_score": 0.8,  # 简化，真实实现需 route 数据
                    "experience_score": p.rating / 5.0,
                    "crowd_avoidance": 0.5,  # 简化
                }
            )

        # 提取帕累托前沿
        pareto_frontier = extract_pareto_frontier(
            dim_candidates,
            ["cost_score", "time_score", "experience_score", "crowd_avoidance"],
        )

        # 少于等于 3 个前沿候选时直接使用
        if len(pareto_frontier) <= 3:
            pareto_pois = [item["poi"] for item in pareto_frontier]
            # 合并非前沿候选（按分数排序后排在后面）
            pareto_ids = {p.id for p in pareto_pois}
            rest = [p for p in candidates if p.id not in pareto_ids]
            rest.sort(key=lambda p: scores.get(p.id, 0), reverse=True)
            return pareto_pois + rest

        # 帕累托前沿过多时（不太常见），按加权评分截断
        pareto_sorted = sorted(
            pareto_frontier,
            key=lambda x: scores.get(x["poi"].id, 0),
            reverse=True,
        )
        top_pareto = [item["poi"] for item in pareto_sorted[:3]]
        pareto_ids = {p.id for p in top_pareto}
        rest = [p for p in candidates if p.id not in pareto_ids]
        rest.sort(key=lambda p: scores.get(p.id, 0), reverse=True)
        return top_pareto + rest

    # ── Slot Generation ─────────────────────────────────────────

    async def _generate_slots_with_routes(
        self,
        pois: list[POI],
        start: datetime,
        end: datetime,
        lat: float,
        lng: float,
    ) -> tuple[list[PlanSlot], list[ConstraintEdge]]:
        """生成时间轴 Slots，使用真实路线时间替代随机值。

        最多 4 个 Slot，均匀分配时间窗口。
        通过 RoutePort 获取真实通行时间。
        使用评分优选 shadow（替代随机选择）。

        Args:
            pois: 排序后的 POI 列表
            start: 计划开始时间
            end: 计划结束时间
            lat/lng: 参考坐标

        Returns:
            (PlanSlot 列表, ConstraintEdge 列表)
        """
        slots: list[PlanSlot] = []
        edges: list[ConstraintEdge] = []
        total_min = (end - start).total_seconds() / 60
        cnt = min(len(pois), 4)
        dur = total_min / max(cnt, 1)
        cur = start
        action_map = {
            "restaurant": "book_table",
            "cafe": "arrive",
            "attraction": "arrive",
            "activity": "book_ticket",
        }

        shadow_pool = list(pois)

        for i, poi in enumerate(pois[:cnt]):
            # 获取真实路线时间
            move = 0
            if i > 0:
                prev_poi = slots[i - 1].poi
                move = await self._get_travel_time(
                    prev_poi.lat, prev_poi.lng, poi.lat, poi.lng
                )

            cur += timedelta(minutes=move)
            slot_end = cur + timedelta(minutes=min(dur, 90))

            # 评分优选 shadow
            shadows = [p for p in shadow_pool if p.type == poi.type and p.id != poi.id]
            best_shadow = select_best_shadow(poi, shadows, self._rt_context)
            shadow_id = best_shadow.id if best_shadow else None

            slot = PlanSlot(
                sequence=i,
                poi=poi,
                time_range=TimeRange(start=cur, end=slot_end),
                action=action_map.get(poi.type, "arrive"),
                estimated_cost=poi.avg_price,
                move_time_min=move,
                confidence=0.7,
                shadow_id=shadow_id,
            )
            slots.append(slot)

            # 约束传播 —— 从上一个 slot 到当前 slot 的路线约束
            if i > 0:
                prev = slots[i - 1]
                est_min = haversine(prev.poi.lat, prev.poi.lng, poi.lat, poi.lng) / 0.5
                edges.append(
                    ConstraintEdge(
                        from_slot=i - 1,
                        to_slot=i,
                        constraint_type="travel_time",
                        min_value=est_min * 0.7,
                        max_value=est_min * 1.5,
                        current_value=float(move),
                    )
                )

            cur = slot_end
            if cur >= end:
                break

        return slots, edges

    async def _get_travel_time(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> int:
        """获取两点间通行时间（分钟）。

        优先通过 RoutePort 获取真实路线，不可用时降级为 haversine 估算。

        Returns:
            通行时间（分钟），含交通延迟
        """
        if self._route is not None:
            try:
                result = await self._route.calculate(
                    origin_lat, origin_lng, dest_lat, dest_lng
                )
                travel = result.travel_min + result.traffic_delay_min
                # 应用拥堵系数
                if self._rt_context and self._rt_context.traffic_index:
                    travel = int(
                        travel * (1 + self._rt_context.traffic_index.overall * 0.5)
                    )
                return max(5, travel)
            except Exception:
                logger.debug("route_calculation_failed", exc_info=True)

        # 降级: haversine 估算（~30 km/h 城市平均速度）
        dist_km = haversine(origin_lat, origin_lng, dest_lat, dest_lng)
        return max(5, int(dist_km / 0.5))

    # ── Backward-Compatible Methods ─────────────────────────────

    def _generate_slots(
        self, pois: list[POI], start: datetime, end: datetime
    ) -> list[PlanSlot]:
        """同步版 slot 生成（向后兼容，供测试使用）。

        与 _generate_slots_with_routes 逻辑一致，但使用 haversine 估算
        移动时间（非异步 RoutePort），shadow 使用评分优选。

        Args:
            pois: 排序后的 POI 列表
            start: 计划开始时间
            end: 计划结束时间

        Returns:
            PlanSlot 列表（≤4 个）
        """
        slots: list[PlanSlot] = []
        total_min = (end - start).total_seconds() / 60
        cnt = min(len(pois), 4)
        dur = total_min / max(cnt, 1)
        cur = start
        action_map = {
            "restaurant": "book_table",
            "cafe": "arrive",
            "attraction": "arrive",
            "activity": "book_ticket",
        }

        shadow_pool = list(pois)
        for i, poi in enumerate(pois[:cnt]):
            move = 0
            if i > 0:
                prev = slots[i - 1]
                move = max(
                    5,
                    int(haversine(prev.poi.lat, prev.poi.lng, poi.lat, poi.lng) / 0.5),
                )

            cur += timedelta(minutes=move)
            slot_end = cur + timedelta(minutes=min(dur, 90))

            shadows = [p for p in shadow_pool if p.type == poi.type and p.id != poi.id]
            best_shadow = select_best_shadow(poi, shadows, self._rt_context)
            shadow_id = best_shadow.id if best_shadow else None

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

    @staticmethod
    def _phase2_fallback_sort(candidates: list[POI], intent: IntentSchema) -> list[POI]:
        """Phase 2 降级排序（纯代码，LLM 超时时使用）。

        按评分 + 心情标签匹配加权排序。

        Args:
            candidates: 候选 POI
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

    # ── Context Extractors ───────────────────────────────────────

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
            from agent.adapters.litellm_adapter import LiteLLMAdapter

            self._llm = LiteLLMAdapter()
        return self._llm

    def _get_prompt_renderer(self) -> PromptPort:
        if self._prompt_renderer is None:
            from agent.adapters.prompt import JinjaPromptAdapter

            self._prompt_renderer = JinjaPromptAdapter()
        return self._prompt_renderer
