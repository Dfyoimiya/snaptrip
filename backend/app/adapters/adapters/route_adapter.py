"""路径规划适配器 —— 高德 direction/walking (或 driving/transit)。

映射到工具 calculate_route (L1) 的 params:
  from_lat / from_lng / to_lat / to_lng / mode (walking|driving|transit)

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from app.adapters.amap_client import get_amap_client
from app.adapters.base import BaseAmapAdapter
from app.adapters.mappers.geo_mapper import GeoMapper
from app.adapters.mappers.route_mapper import RouteMapper
from app.adapters.schemas.route import AmapRouteResponse


class AmapRouteAdapter(BaseAmapAdapter):
    """高德路径规划适配器"""

    tool_name = "calculate_route"

    async def validate(self, params: dict) -> bool:
        return all(k in params for k in ("from_lat", "from_lng", "to_lat", "to_lng"))

    async def _call_api(self, params: dict) -> dict:
        client = get_amap_client()
        mode = params.get("mode", "walking")  # walking / driving / transit

        origin = GeoMapper.format_location(
            float(params["from_lat"]), float(params["from_lng"])
        )
        destination = GeoMapper.format_location(
            float(params["to_lat"]), float(params["to_lng"])
        )

        resp = await client.get(
            f"/v3/direction/{mode}",
            params={"origin": origin, "destination": destination},
        )

        response = AmapRouteResponse(**resp)
        return RouteMapper.to_route_summary(response.route.paths)
