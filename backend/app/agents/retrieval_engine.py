"""Retrieval Engine — 并行 POI 检索"""

from __future__ import annotations

import asyncio
import math
import random

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.core.constants import RETRIEVAL_TIMEOUT_S
from app.data.seed_pois import SEED_POIS
from app.schemas.plan import CandidatePool, EnrichedIntent, IntentSchema, POI

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

        type_groups = {"restaurant": [], "cafe": [], "attraction": [], "activity": []}
        for p in pois:
            if intent.city and p.city != intent.city:
                continue
            dist = haversine(lat, lng, p.lat, p.lng)
            if dist > 15.0:
                continue
            p.avg_price = p.avg_price
            type_groups.get(p.type, type_groups["attraction"]).append(p)

        candidates = []
        for t in (intent.type_prefs or ["restaurant", "cafe", "attraction", "activity"]):
            candidates.extend(type_groups.get(t, [])[:5])

        if not candidates:
            candidates = [random.choice(pois) for _ in range(min(5, len(pois)))]

        pool = CandidatePool(candidates=candidates[:20], total=len(candidates))
        return AgentResult(data={"candidate_pool": pool.model_dump()})
