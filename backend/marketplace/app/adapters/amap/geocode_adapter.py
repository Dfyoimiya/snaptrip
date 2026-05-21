"""地理编码适配器 —— 高德 geocode/geo + geocode/regeo。

支持:
  - geocode_address: 地址 → 坐标 (geocode/geo)
  - reverse_geocode: 坐标 → 地址 (geocode/regeo)

新增工具:
  - geocode_address (L0): params = {address}
  - reverse_geocode (L0): params = {lat, lng}

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from marketplace.app.adapters.amap.base import BaseAmapAdapter
from marketplace.app.adapters.amap.client import get_amap_client
from marketplace.app.adapters.amap.schemas.geocode import AmapGeoResponse, AmapRegeoResponse


class AmapGeocodeAdapter(BaseAmapAdapter):
    """高德地理编码适配器 (address → lat/lng)"""

    tool_name = "geocode_address"

    async def validate(self, params: dict) -> bool:
        return bool(params.get("address"))

    async def _call_api(self, params: dict) -> dict:
        client = get_amap_client()
        city = params.get("city", "")
        resp = await client.get(
            "/v3/geocode/geo",
            params={"address": params["address"], "city": city or ""},
        )
        response = AmapGeoResponse(**resp)

        results = []
        for geo in response.geocodes:
            lat, lng = 0.0, 0.0
            if geo.location and "," in geo.location:
                parts = geo.location.split(",", 1)
                try:
                    lng = float(parts[0])
                    lat = float(parts[1])
                except (ValueError, IndexError):
                    pass
            results.append(
                {
                    "formatted_address": geo.formatted_address,
                    "province": geo.province,
                    "city": geo.city,
                    "district": geo.district,
                    "lat": lat,
                    "lng": lng,
                    "level": geo.level,
                }
            )

        return {
            "results": results,
            "count": int(response.count or 0),
            "source": "amap",
        }


class AmapReGeocodeAdapter(BaseAmapAdapter):
    """高德逆地理编码适配器 (lat/lng → address)"""

    tool_name = "reverse_geocode"

    async def validate(self, params: dict) -> bool:
        return "lat" in params and "lng" in params

    async def _call_api(self, params: dict) -> dict:
        client = get_amap_client()
        location = f"{params['lng']},{params['lat']}"
        resp = await client.get(
            "/v3/geocode/regeo",
            params={"location": location, "extensions": "base"},
        )
        response = AmapRegeoResponse(**resp)
        component = response.regeocode.addressComponent

        return {
            "formatted_address": response.regeocode.formatted_address,
            "province": component.province,
            "city": component.city,
            "citycode": component.citycode,
            "district": component.district,
            "adcode": component.adcode,
            "township": component.township,
            "source": "amap",
        }
