"""AmapPOITool — POI search via Amap API.

Searches activities, restaurants, and delivery options near a location.
Read-only tool; compensation is cache invalidation (no-op).

决不兜底种子数据。高德 API 无结果就是无结果，如实返回空列表。
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

logger = logging.getLogger(__name__)


class POISearchInput(BaseModel):
    """Input schema for Amap POI search."""

    lat: float = Field(description="Latitude")
    lng: float = Field(description="Longitude")
    radius_km: float = Field(default=10.0, description="Search radius in km")
    keywords: str = Field(default="", description="Search keywords")
    category: str = Field(default="", description="POI category: restaurant/park/museum/playground")
    max_results: int = Field(default=20, ge=1, le=20)
    child_friendly: bool = Field(default=False)
    budget_per_person: int = Field(default=500)


class AmapPOITool(SmartDayBaseTool):
    """Search nearby POIs via Amap REST API (MCP-first, REST fallback)."""

    name: str = "amap_poi_search"
    description: str = (
        "Search for points of interest (activities, restaurants, delivery) near a "
        "location. Use this tool when the user asks for nearby places to visit or eat. "
        "Returns results with name, address, rating, coordinates, and child-friendly flag. "
        "If the Amap API returns no results, returns an empty list — never fabricates data."
    )
    args_schema: type[BaseModel] = POISearchInput
    is_read_only: bool = True
    cost_model: str = "free"
    tool_timeout: float = 5.0

    async def _arun(
        self,
        lat: float,
        lng: float,
        radius_km: float = 10.0,
        keywords: str = "",
        category: str = "",
        max_results: int = 20,
        child_friendly: bool = False,
        budget_per_person: int = 500,
        **kwargs: Any,
    ) -> ToolResult:
        """Search POIs via Amap API. Returns empty list on failure — no seed data."""
        try:
            pois = await self._search_amap(
                lat=lat, lng=lng, radius_km=radius_km,
                keywords=keywords, category=category,
                max_results=max_results,
            )
        except Exception as e:
            logger.warning("Amap POI search failed: %s", e)
            return ToolResult(
                success=False,
                data={"pois": [], "count": 0, "error": str(e)},
                cost_cny=0.0,
            )

        filtered = [p for p in pois if not (
            (child_friendly and not p.get("child_friendly", False))
            or (p.get("avg_price", 0) > budget_per_person)
        )]
        filtered.sort(key=lambda x: x.get("rating", 0), reverse=True)

        return ToolResult(
            success=True,
            data={"pois": filtered[:max_results], "count": len(filtered[:max_results])},
            cost_cny=0.0,
            idempotency_key=self._idem_key({
                "lat": lat, "lng": lng, "radius_km": radius_km, "keywords": keywords,
            }),
        )

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        return self._noop_compensation(
            action_id=f"cache_invalidate:{result.idempotency_key}",
            tool_name=self.name,
        )

    async def _search_amap(
        self, lat: float, lng: float, radius_km: float,
        keywords: str, category: str, max_results: int,
    ) -> list[dict[str, Any]]:
        from agent.adapters.amap_adapter import get_adapter, ACTIVITY_TYPECODES, RESTAURANT_TYPECODES
        adapter = get_adapter()
        location = f"{lng},{lat}"
        radius_m = int(radius_km * 1000)
        types = ""
        if category:
            codes_map = {**ACTIVITY_TYPECODES, **RESTAURANT_TYPECODES}
            code = codes_map.get(category, "")
            if code:
                types = code
        pois = await adapter.search_pois_around(
            location=location, radius=radius_m,
            keywords=keywords, types=types, offset=max_results,
        )
        return pois
