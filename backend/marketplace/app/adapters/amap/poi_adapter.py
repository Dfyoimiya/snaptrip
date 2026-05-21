"""POI 搜索适配器 —— 高德 place/around 或 place/text。

支持两种搜索模式:
  - 周边搜索: lat/lng + radius → /v3/place/around
  - 关键字搜索: keywords + city → /v3/place/text

映射到工具 search_poi (L0) 的 params:
  city / category / lat / lng / radius_km

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from marketplace.app.adapters.amap.base import BaseAmapAdapter
from marketplace.app.adapters.amap.client import get_amap_client
from marketplace.app.adapters.amap.poi_mapper import PoiMapper
from marketplace.app.adapters.amap.schemas.poi import AmapPoiResponse

AMAP_CATEGORY_KEYWORDS: dict[str, str] = {
    "restaurant": "餐饮|美食|餐厅",
    "cafe": "咖啡|茶馆|咖啡馆",
    "attraction": "景点|公园|博物馆",
    "activity": "电影院|KTV|密室|桌游",
}


class AmapPoiAdapter(BaseAmapAdapter):
    """高德 POI 搜索适配器"""

    tool_name = "search_poi"

    async def validate(self, params: dict) -> bool:
        return bool(params.get("city") or params.get("keywords"))

    async def _call_api(self, params: dict) -> dict:
        client = get_amap_client()

        lat = params.get("lat")
        lng = params.get("lng")
        radius_m = int((params.get("radius_km") or 5) * 1000)

        keywords = params.get("keywords", "")
        if not keywords and params.get("category"):
            keywords = AMAP_CATEGORY_KEYWORDS.get(params["category"], params["category"])

        city = params.get("city", "")
        limit = params.get("limit", 0) or 20

        if lat is not None and lng is not None and not keywords:
            resp = await client.get(
                "/v3/place/around",
                params={
                    "location": f"{lng},{lat}",
                    "radius": str(radius_m),
                    "types": AMAP_CATEGORY_KEYWORDS.get(params.get("category", ""), ""),
                    "offset": str(limit),
                    "page": "1",
                    "extensions": "all",
                },
            )
        else:
            resp = await client.get(
                "/v3/place/text",
                params={
                    "keywords": keywords or city,
                    "city": city if keywords else "",
                    "offset": str(limit),
                    "page": "1",
                    "extensions": "all",
                },
            )

        response = AmapPoiResponse(**resp)
        internal_pois = PoiMapper.to_internal_batch(response.pois, city_override=city)

        return {
            "pois": [p.model_dump() for p in internal_pois],
            "total": int(response.count or 0),
            "source": "amap",
        }
