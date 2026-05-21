"""行政区划查询适配器 —— 高德 config/district。

新增工具:
  - search_district (L0): params = {keywords, subdistrict}

用途:
  获取城市/区域边界、中心坐标，辅助 RetrievalEngine 的城市坐标映射。

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from marketplace.app.adapters.amap.base import BaseAmapAdapter
from marketplace.app.adapters.amap.client import get_amap_client
from marketplace.app.adapters.amap.schemas.district import AmapDistrictResponse


class AmapDistrictAdapter(BaseAmapAdapter):
    """高德行政区划查询适配器"""

    tool_name = "search_district"

    async def validate(self, params: dict) -> bool:
        return bool(params.get("keywords"))

    async def _call_api(self, params: dict) -> dict:
        client = get_amap_client()
        resp = await client.get(
            "/v3/config/district",
            params={
                "keywords": params["keywords"],
                "subdistrict": str(params.get("subdistrict", 1)),
            },
        )
        response = AmapDistrictResponse(**resp)

        results = []
        for dist in response.districts:
            center_lat, center_lng = 0.0, 0.0
            if dist.center and "," in dist.center:
                try:
                    lng_str, lat_str = dist.center.split(",", 1)
                    center_lng = float(lng_str)
                    center_lat = float(lat_str)
                except (ValueError, IndexError):
                    pass

            results.append(
                {
                    "name": dist.name,
                    "adcode": dist.adcode,
                    "citycode": dist.citycode,
                    "center_lat": center_lat,
                    "center_lng": center_lng,
                    "level": dist.level,
                    "sub_count": len(dist.districts),
                }
            )

        return {
            "results": results,
            "count": int(response.count or 0),
            "source": "amap",
        }
