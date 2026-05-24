"""Retrieval Engine —— 并行 POI 检索（支持实时 Amap + 种子兜底）。

执行流程:
  1. 读取 EnrichedIntent，获取城市、类型偏好、搜索关键词
  2. 优先通过 POISearchPort 调用高德 POI API 获取真实数据
  3. API 不可用时自动降级到种子 POI 数据
  4. 若 RTContextPort 可用，为每个 POI 附加 POIRealTimeStatus
  5. haversine 距离过滤 + 类型分组 → CandidatePool

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import math
import random
from typing import Any, Protocol

from snaptrip_shared.schemas.plan import POI, CandidatePool, IntentSchema

from agent.protocol import AgentContext, AgentResult, BaseAgent
from marketplace.app.data.seed_pois import SEED_POIS

CITY_CENTERS: dict[str, tuple[float, float]] = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "重庆": (29.5630, 106.5516),
}

POI_TYPE_ORDER = ["restaurant", "cafe", "attraction", "activity"]

# 高德 POI 类型 → 分类关键词映射
AMAP_CATEGORY_KEYWORDS: dict[str, str] = {
    "restaurant": "餐饮|美食|餐厅",
    "cafe": "咖啡|茶馆|咖啡馆",
    "attraction": "景点|公园|博物馆",
    "activity": "电影院|KTV|密室|桌游",
}


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
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


class POISearchPort(Protocol):
    """POI 搜索端口 —— 由 AmapPoiAdapter 或 MockGateway 实现。

    检索引擎通过此端口获取真实 POI 数据，不直接依赖 marketplace 适配器。
    """

    async def search(
        self,
        *,
        city: str = "",
        lat: float | None = None,
        lng: float | None = None,
        keywords: str = "",
        category: str = "",
        radius_km: float = 10.0,
        limit: int = 20,
    ) -> list[POI]:
        """搜索 POI 列表。

        Args:
            city: 城市名（用于文本搜索）
            lat/lng: 中心坐标（用于周边搜索）
            keywords: 搜索关键词
            category: POI 分类 (restaurant/cafe/attraction/activity)
            radius_km: 周边搜索半径（km）
            limit: 返回数量上限

        Returns:
            POI 列表，API 失败时返回空列表
        """
        ...


class RetrievalEngine(BaseAgent):
    name = "retrieval_engine"

    def __init__(
        self,
        poi_search: POISearchPort | None = None,
    ) -> None:
        """初始化检索引擎。

        Args:
            poi_search: POI 搜索端口。为 None 时仅使用种子数据。
        """
        super().__init__()
        self._poi_search = poi_search

    async def execute(self, context: AgentContext) -> AgentResult:
        """执行 POI 检索：实时 API → 种子兜底 → 距离过滤 → 类型分组 → 候选池。

        Args:
            context: 含 EnrichedIntent 的上下文

        Returns:
            AgentResult.data["candidate_pool"] = CandidatePool
        """
        enriched_data = self._extract_enriched_intent(context)
        intent = (
            IntentSchema(**enriched_data.get("intent", {}))
            if enriched_data.get("intent")
            else IntentSchema()
        )

        lat, lng = self._resolve_center(intent, context)

        # Phase 1: 尝试通过高德 API 搜索 POI
        pois = await self._search_pois(intent, lat, lng)

        # Phase 2: 距离过滤
        pois = self._filter_by_distance(pois, lat, lng, radius_km=15.0)

        # Phase 3: 按类型分组 + 偏好排序
        candidates = self._build_candidates(pois, intent)

        # Phase 4: 兜底 —— 无候选时使用种子数据
        if not candidates:
            candidates = self._fallback_seeds()

        pool = CandidatePool(candidates=candidates[:20], total=len(candidates))
        return AgentResult(data={"candidate_pool": pool.model_dump()})

    # ── helper methods ──────────────────────────────────────────────

    @staticmethod
    def _extract_enriched_intent(context: AgentContext) -> dict[str, Any]:
        for h in reversed(context.history):
            if "enriched_intent" in h.data:
                return dict(h.data["enriched_intent"])
        return {}

    @staticmethod
    def _resolve_center(
        intent: IntentSchema, context: AgentContext
    ) -> tuple[float, float]:
        if intent.city and intent.city in CITY_CENTERS:
            return CITY_CENTERS[intent.city]
        return context.lat, context.lng

    async def _search_pois(
        self,
        intent: IntentSchema,
        lat: float,
        lng: float,
    ) -> list[POI]:
        """通过 POISearchPort 搜索 POI，不可用时返回种子数据。"""
        if self._poi_search is None:
            return [POI(**p.model_dump()) for p in SEED_POIS]

        try:
            all_pois: list[POI] = []
            type_prefs = intent.type_prefs or POI_TYPE_ORDER

            # 对每种偏好类型分别搜索，提升多样性
            for category in type_prefs:
                pois = await self._poi_search.search(
                    city=intent.city or "",
                    lat=lat,
                    lng=lng,
                    keywords=intent.query or "",
                    category=category,
                    radius_km=10.0,
                    limit=10,
                )
                all_pois.extend(pois)

            if all_pois:
                return all_pois
        except Exception:
            pass  # 静默降级到种子数据

        # 降级：返回种子数据
        return [POI(**p.model_dump()) for p in SEED_POIS]

    @staticmethod
    def _filter_by_distance(
        pois: list[POI],
        lat: float,
        lng: float,
        radius_km: float = 15.0,
    ) -> list[POI]:
        """haversine 距离过滤。"""
        return [p for p in pois if haversine(lat, lng, p.lat, p.lng) <= radius_km]

    @staticmethod
    def _build_candidates(pois: list[POI], intent: IntentSchema) -> list[POI]:
        """按类型分组，返回偏好类型 TOP 5。"""
        type_groups: dict[str, list[POI]] = {t: [] for t in POI_TYPE_ORDER}
        for p in pois:
            group = type_groups.get(p.type)
            if group is not None:
                group.append(p)
            else:
                type_groups["attraction"].append(p)

        candidates: list[POI] = []
        for t in intent.type_prefs or POI_TYPE_ORDER:
            candidates.extend(type_groups.get(t, [])[:5])
        return candidates

    @staticmethod
    def _fallback_seeds() -> list[POI]:
        """种子数据兜底 —— 随机选取 5 个 POI。"""
        pois = [POI(**p.model_dump()) for p in SEED_POIS]
        return [random.choice(pois) for _ in range(min(5, len(pois)))]
