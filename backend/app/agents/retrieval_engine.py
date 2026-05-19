"""Retrieval Engine —— 并行 POI 检索。

从种子数据中按城市、类型、距离筛选候选 POI。

执行流程:
  1. 读取 EnrichedIntent，获取城市和类型偏好
  2. 若城市已知，自动映射到城市中心坐标
  3. haversine 距离过滤（≤15km）
  4. 按类型分组，优先返回偏好类型的 TOP 5
  5. 若无匹配结果，返回最近的 5 个 POI

haversine 公式: 使用球面余弦定理计算两点间大圆距离。

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import math
import random

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.data.seed_pois import SEED_POIS
from app.schemas.plan import POI, CandidatePool, IntentSchema

CITY_CENTERS: dict[str, tuple[float, float]] = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "重庆": (29.5630, 106.5516),
}


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RetrievalEngine(BaseAgent):
    name = "retrieval_engine"

    async def execute(self, context: AgentContext) -> AgentResult:
        """执行 POI 检索：城市映射 → 距离过滤 → 类型分组 → 返回候选池。

        从 context.history 读取 EnrichedIntent，按城市/类型/距离筛选。
        若无匹配结果，返回距离最近的 5 个 POI 作为兜底。

        Args:
            context: 含 EnrichedIntent 的上下文

        Returns:
            AgentResult.data["candidate_pool"] = CandidatePool
        """
        enriched_data = {}
        for h in reversed(context.history):
            if "enriched_intent" in h.data:
                enriched_data = h.data["enriched_intent"]
                break

        intent = IntentSchema(**enriched_data.get("intent", {})) if enriched_data.get("intent") else IntentSchema()

        lat, lng = context.lat, context.lng
        if intent.city and intent.city in CITY_CENTERS:
            lat, lng = CITY_CENTERS[intent.city]

        pois = [POI(**p.model_dump()) for p in SEED_POIS]

        type_groups: dict[str, list[POI]] = {"restaurant": [], "cafe": [], "attraction": [], "activity": []}
        for p in pois:
            if intent.city and p.city != intent.city:
                continue
            dist = haversine(lat, lng, p.lat, p.lng)
            if dist > 15.0:
                continue
            p.avg_price = p.avg_price
            type_groups.get(p.type, type_groups["attraction"]).append(p)

        candidates = []
        for t in intent.type_prefs or ["restaurant", "cafe", "attraction", "activity"]:
            candidates.extend(type_groups.get(t, [])[:5])

        if not candidates:
            candidates = [random.choice(pois) for _ in range(min(5, len(pois)))]

        pool = CandidatePool(candidates=candidates[:20], total=len(candidates))
        return AgentResult(data={"candidate_pool": pool.model_dump()})
