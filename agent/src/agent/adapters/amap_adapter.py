"""高德地图适配器 —— REST API + MCP 专属功能。

检索/地理编码/天气/路径规划直接走 REST API (restapi.amap.com)。
专属地图/导航/打车走 MCP (mcp.amap.com)。

Author: SnapTrip Team
Date: 2026-05-27
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from agent.ports.tools import ToolPort

logger = logging.getLogger(__name__)

AMAP_REST_BASE = "https://restapi.amap.com"

_MCP_URL_TEMPLATE = "https://mcp.amap.com/mcp?key={key}"


def _get_api_key() -> str:
    """从 shared settings 获取 Amap API key（pydantic-settings 自动读取环境变量）。"""
    from snaptrip_shared.core.config import settings
    return settings.AMAP_API_KEY


def _get_mcp_url() -> str:
    key = _get_api_key()
    if not key:
        raise RuntimeError("AMAP_API_KEY not configured")
    return _MCP_URL_TEMPLATE.format(key=key)


def _get_ssl_verify() -> bool:
    """生产环境强制 SSL 验证，本地开发可通过 AMAP_SSL_VERIFY=0 关闭。"""
    from snaptrip_shared.core.config import settings
    return settings.AMAP_SSL_VERIFY

# ── POI 类型码表（高德分类编码）────────────────────────────
# 用于将内部 activity_types / restaurant_types 映射为高德 typecode
ACTIVITY_TYPECODES = {
    "attraction": "110000",   # 风景名胜
    "museum": "140000",       # 科教文化服务
    "park": "110100",         # 公园广场
    "zoo": "110200",          # 动物园
    "bar": "080300",          # 酒吧
    "live_house": "080400",   # 音乐厅
    "shopping": "060000",     # 购物服务
    "escape_room": "080500",  # 娱乐场所
}
RESTAURANT_TYPECODES = {
    "chinese": "050100",      # 中餐厅
    "western": "050200",      # 西餐厅
    "japanese": "050300",     # 日韩料理
    "hotpot": "050101",       # 火锅
    "bbq": "050102",          # 烧烤
    "cafe": "050500",         # 咖啡厅
    "bar": "080300",          # 酒吧
    "family_style": "050100", # 家庭风格→中餐
}


# ═══════════════════════════════════════════════════════════════
# AmapAdapter
# ═══════════════════════════════════════════════════════════════

class AmapAdapter(ToolPort):
    """高德 REST + MCP 适配器。

    检索/地理编码/天气/路径规划 → REST API。
    专属地图/导航/打车 → MCP（无 REST 替代）。
    MCP session 在首次调用时惰性建立并缓存复用。
    """

    def __init__(self, mcp_url: str = "", api_key: str = "") -> None:
        self._mcp_url = mcp_url or _get_mcp_url()
        self._api_key = api_key or _get_api_key()
        self._mcp_verify = _get_ssl_verify()

        # REST client — 惰性初始化
        self._rest: httpx.AsyncClient | None = None

        # MCP session 缓存 — 惰性建立，复用
        self._mcp_session: ClientSession | None = None
        self._mcp_context: tuple[Any, Any, Any] | None = None
        self._mcp_lock = asyncio.Lock()

    @property
    def rest(self) -> httpx.AsyncClient:
        """惰性初始化 REST client。"""
        if self._rest is None:
            self._rest = httpx.AsyncClient(
                base_url=AMAP_REST_BASE,
                timeout=httpx.Timeout(15.0),
                params={"key": self._api_key},
            )
        return self._rest

    async def close(self) -> None:
        """释放所有连接资源。"""
        if self._rest:
            await self._rest.aclose()
            self._rest = None
        if self._mcp_session:
            try:
                await self._mcp_session.__aexit__(None, None, None)
            except Exception:
                pass
            self._mcp_session = None
            self._mcp_context = None

    async def __aenter__(self) -> AmapAdapter:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── MCP 调用辅助 ──────────────────────────────────────────

    async def _get_mcp_session(self) -> ClientSession:
        """惰性建立 MCP session 并缓存复用。"""
        async with self._mcp_lock:
            if self._mcp_session is not None:
                return self._mcp_session

            _factory = lambda *a, **kw: httpx.AsyncClient(
                verify=self._mcp_verify,
                timeout=kw.pop("timeout", httpx.Timeout(10.0)),
                **kw,
            )
            ctx = streamablehttp_client(
                self._mcp_url, httpx_client_factory=_factory,
            )
            read, write, get_session_id = await ctx.__aenter__()
            session = ClientSession(read, write)
            await session.initialize()

            self._mcp_context = (read, write, get_session_id)
            self._mcp_session = session
            return session

    async def _call_mcp(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """调用 MCP tool，失败抛异常。复用缓存的 session。"""
        session = await self._get_mcp_session()
        result = await session.call_tool(tool_name, arguments)
        return result.content

    async def _call_mcp_safe(self, tool_name: str, arguments: dict[str, Any]) -> Any | None:
        """安全调用 MCP，失败返回 None（触发 REST 降级）。"""
        try:
            return await self._call_mcp(tool_name, arguments)
        except Exception as e:
            logger.warning("MCP call %s failed: %s", tool_name, e)
            return None

    # ── 搜索 ──────────────────────────────────────────────────

    async def search_pois_by_keyword(
        self, keywords: str, city: str = "", types: str = "",
        offset: int = 10, page: int = 1,
    ) -> list[dict[str, Any]]:
        return await self._rest_keyword_search(keywords, city, types, offset, page)

    async def search_pois_around(
        self, location: str, radius: int = 5000,
        keywords: str = "", types: str = "", offset: int = 10,
    ) -> list[dict[str, Any]]:
        return await self._rest_around_search(location, radius, keywords, types, offset)

    async def get_poi_detail(self, poi_ids: list[str]) -> list[dict[str, Any]]:
        if not poi_ids:
            return []
        ids_str = "|".join(poi_ids)
        try:
            resp = await self.rest.get(
                "/v5/place/detail",
                params={"id": ids_str, "show_fields": "business,photos,navi"},
            )
            data = resp.json()
            if data.get("status") == "1":
                return [_rest_poi_to_internal(p) for p in data.get("pois", [])]
        except Exception as e:
            logger.warning("REST detail search failed: %s", e)
        return []

    async def input_tips(
        self, keywords: str, city: str = "", location: str = "",
    ) -> list[dict[str, Any]]:
        # 仅 REST
        params: dict[str, Any] = {"keywords": keywords}
        if city:
            params["city"] = city
        if location:
            params["location"] = location
        try:
            resp = await self.rest.get("/v3/assistant/inputtips", params=params)
            data = resp.json()
            if data.get("status") == "1":
                tips = []
                for t in data.get("tips", []):
                    loc = t.get("location", "")
                    lng, lat = (loc.split(",") if loc else ("0", "0"))
                    tips.append({
                        "id": t.get("id", ""),
                        "name": t.get("name", ""),
                        "district": t.get("district", ""),
                        "adcode": t.get("adcode", ""),
                        "lng": float(lng),
                        "lat": float(lat),
                    })
                return tips
        except Exception as e:
            logger.warning("input_tips failed: %s", e)
        return []

    # ── 地理编码 ──────────────────────────────────────────────

    async def geocode(self, address: str, city: str = "") -> dict[str, Any]:
        params: dict[str, Any] = {"address": address}
        if city:
            params["city"] = city
        try:
            resp = await self.rest.get("/v3/geocode/geo", params=params)
            data = resp.json()
            if data.get("status") == "1" and data.get("geocodes"):
                gc = data["geocodes"][0]
                loc = gc.get("location", "0,0")
                lng_str, lat_str = loc.split(",")
                return {
                    "lng": float(lng_str),
                    "lat": float(lat_str),
                    "adcode": gc.get("adcode", ""),
                    "city": gc.get("city", ""),
                    "district": gc.get("district", ""),
                    "address": gc.get("formatted_address", address),
                    "level": gc.get("level", ""),
                }
        except Exception as e:
            logger.warning("geocode failed: %s", e)
        return {"lng": 0, "lat": 0}

    async def reverse_geocode(
        self, location: str, radius: int = 1000, with_pois: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"location": location, "radius": radius}
        if with_pois:
            params["extensions"] = "all"
        try:
            resp = await self.rest.get("/v3/geocode/regeo", params=params)
            data = resp.json()
            if data.get("status") == "1":
                rg = data.get("regeocode", {})
                ac = rg.get("addressComponent", {})
                result = {
                    "address": rg.get("formatted_address", ""),
                    "province": ac.get("province", ""),
                    "city": ac.get("city", ""),
                    "district": ac.get("district", ""),
                    "adcode": ac.get("adcode", ""),
                    "township": ac.get("township", ""),
                }
                if with_pois:
                    result["pois"] = [
                        _rest_regeo_poi(p) for p in rg.get("pois", [])
                    ]
                    result["roads"] = rg.get("roads", [])
                    result["business_areas"] = [
                        ba.get("name") for ba in ac.get("businessAreas", [])
                    ]
                return result
        except Exception as e:
            logger.warning("reverse_geocode failed: %s", e)
        return {}

    async def ip_location(self, ip: str = "") -> dict[str, Any]:
        params: dict[str, Any] = {}
        if ip:
            params["ip"] = ip
        try:
            resp = await self.rest.get("/v3/ip", params=params)
            data = resp.json()
            if data.get("status") == "1":
                rect = data.get("rectangle", "")
                center_lng, center_lat = ("0", "0")
                if rect:
                    parts = rect.split(";")
                    if len(parts) == 2:
                        left_bottom = [float(x) for x in parts[0].split(",")]
                        right_top = [float(x) for x in parts[1].split(",")]
                        center_lng = str((left_bottom[0] + right_top[0]) / 2)
                        center_lat = str((left_bottom[1] + right_top[1]) / 2)
                return {
                    "province": data.get("province", ""),
                    "city": data.get("city", ""),
                    "adcode": data.get("adcode", ""),
                    "location": f"{center_lng},{center_lat}",
                }
        except Exception as e:
            logger.warning("ip_location failed: %s", e)
        return {}

    async def get_district(
        self, keywords: str, subdistrict: int = 1,
    ) -> list[dict[str, Any]]:
        # 仅 REST
        try:
            resp = await self.rest.get(
                "/v3/config/district",
                params={"keywords": keywords, "subdistrict": subdistrict},
            )
            data = resp.json()
            if data.get("status") == "1":
                return _parse_districts(data.get("districts", []))
        except Exception as e:
            logger.warning("get_district failed: %s", e)
        return []

    # ── 天气 ──────────────────────────────────────────────────

    async def get_weather(
        self, city_adcode: str, forecast: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"city": city_adcode}
        if forecast:
            params["extensions"] = "all"
        else:
            params["extensions"] = "base"
        try:
            resp = await self.rest.get("/v3/weather/weatherInfo", params=params)
            data = resp.json()
            if data.get("status") == "1":
                if forecast:
                    fcs = data.get("forecasts", [{}])[0]
                    return {
                        "city": fcs.get("city", ""),
                        "adcode": fcs.get("adcode", ""),
                        "forecasts": [
                            {
                                "date": c.get("date", ""),
                                "week": c.get("week", ""),
                                "day_weather": c.get("dayweather", ""),
                                "night_weather": c.get("nightweather", ""),
                                "day_temp": c.get("daytemp", ""),
                                "night_temp": c.get("nighttemp", ""),
                            }
                            for c in fcs.get("casts", [])
                        ],
                    }
                lives = data.get("lives", [{}])[0]
                return {
                    "city": lives.get("city", ""),
                    "weather": lives.get("weather", ""),
                    "temperature": lives.get("temperature", ""),
                    "wind_direction": lives.get("winddirection", ""),
                    "wind_power": lives.get("windpower", ""),
                    "humidity": lives.get("humidity", ""),
                }
        except Exception as e:
            logger.warning("get_weather failed: %s", e)
        return {}

    # ── 路径规划 ──────────────────────────────────────────────

    async def estimate_travel_time(
        self, origin: str, destination: str, mode: str = "driving",
    ) -> dict[str, Any]:
        return await self._rest_travel_time(origin, destination, mode)

    async def get_route_plan(
        self, origin: str, destination: str,
        mode: str = "driving", strategy: int = 32,
        city1: str = "", city2: str = "",
    ) -> dict[str, Any]:
        return await self._rest_route(origin, destination, mode, strategy, city1, city2)

    # ── MCP 专属 ──────────────────────────────────────────────

    async def generate_custom_map(
        self, title: str, daily_schedules: list[dict[str, Any]],
    ) -> str:
        args: dict[str, Any] = {
            "title": title,
            "daily_schedules": daily_schedules,
        }
        result = await self._call_mcp_safe("maps_schema_personal_map", args)
        if result:
            for item in result:
                if hasattr(item, "text") and item.text:
                    return item.text
        return ""

    async def navigate_to_destination(self, location: str) -> str:
        result = await self._call_mcp_safe("maps_schema_navi", {"location": location})
        if result:
            for item in result:
                if hasattr(item, "text") and item.text:
                    return item.text
        return ""

    async def hail_ride(self, origin: str, destination: str) -> str:
        result = await self._call_mcp_safe("maps_schema_take_taxi", {
            "origin": origin, "destination": destination,
        })
        if result:
            for item in result:
                if hasattr(item, "text") and item.text:
                    return item.text
        return ""

    # ── 内部 REST 方法 ────────────────────────────────────────

    async def _rest_keyword_search(
        self, keywords: str, city: str, types: str, offset: int, page: int,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "keywords": keywords, "offset": offset, "page": page,
            "show_fields": "business,photos",
        }
        if types:
            params["types"] = types
        if city:
            params["region"] = city
        try:
            resp = await self.rest.get("/v5/place/text", params=params)
            data = resp.json()
            if data.get("status") == "1":
                return [_rest_poi_to_internal(p) for p in data.get("pois", [])]
        except Exception as e:
            logger.warning("REST keyword search failed: %s", e)
        return []

    async def _rest_around_search(
        self, location: str, radius: int, keywords: str, types: str, offset: int,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "location": location, "radius": radius, "offset": offset,
            "show_fields": "business,photos",
        }
        if keywords:
            params["keywords"] = keywords
        if types:
            params["types"] = types
        try:
            resp = await self.rest.get("/v5/place/around", params=params)
            data = resp.json()
            if data.get("status") == "1":
                return [_rest_poi_to_internal(p) for p in data.get("pois", [])]
        except Exception as e:
            logger.warning("REST around search failed: %s", e)
        return []

    async def _enrich_pois(self, pois: list[dict]) -> list[dict[str, Any]]:
        """用 REST detail 批量补全 MCP 返回的 POI 增强字段。"""
        ids = [p["id"] for p in pois if p.get("id")]
        if not ids:
            return pois
        try:
            ids_str = "|".join(ids[:10])  # 最多10个批量查
            resp = await self.rest.get(
                "/v5/place/detail",
                params={"id": ids_str, "show_fields": "business,photos,children"},
            )
            data = resp.json()
            if data.get("status") == "1":
                detail_map = {p["id"]: p for p in data.get("pois", [])}
                for poi in pois:
                    detail = detail_map.get(poi["id"])
                    if detail:
                        _merge_detail_fields(poi, detail)
        except Exception as e:
            logger.warning("POI enrich failed: %s", e)
        return pois

    async def _rest_travel_time(
        self, origin: str, destination: str, mode: str,
    ) -> dict[str, Any]:
        path_data = await self._rest_route(origin, destination, mode)
        return {
            "distance_km": round(float(path_data.get("distance", 0)) / 1000, 2),
            "duration_min": round(float(path_data.get("duration", 0)) / 60, 1),
        }

    async def _rest_route(
        self, origin: str, destination: str, mode: str,
        strategy: int = 32, city1: str = "", city2: str = "",
    ) -> dict[str, Any]:
        url_map = {
            "driving": "/v5/direction/driving",
            "walking": "/v5/direction/walking",
            "cycling": "/v5/direction/bicycling",
            "transit": "/v5/direction/transit/integrated",
        }
        url = url_map.get(mode, "/v5/direction/driving")
        params: dict[str, Any] = {
            "origin": origin, "destination": destination,
            "show_fields": "cost",
        }
        if mode == "driving":
            params["strategy"] = str(strategy)
        if mode == "transit":
            params["city1"] = city1 or "010"
            params["city2"] = city2 or "010"
        try:
            resp = await self.rest.get(url, params=params)
            data = resp.json()
            if data.get("status") == "1":
                route = data.get("route", {})
                paths = route.get("paths", [])
                if not paths:
                    return {}
                # 对于 transit，paths 在 transits 下
                if mode == "transit":
                    transits = route.get("transits", [])
                    if transits:
                        t = transits[0]
                        return {
                            "distance": t.get("distance", "0"),
                            "duration": t.get("cost", {}).get("duration", "0"),
                            "taxi_cost": t.get("cost", {}).get("taxi_fee", "0"),
                            "transit_fee": t.get("cost", {}).get("transit_fee", "0"),
                        }
                p = paths[0]
                return {
                    "distance": p.get("distance", "0"),
                    "duration": p.get("cost", {}).get("duration", "0"),
                    "taxi_cost": route.get("taxi_cost", "0"),
                    "tolls": p.get("cost", {}).get("tolls", "0"),
                    "traffic_lights": p.get("traffic_lights", "0"),
                }
        except Exception as e:
            logger.warning("REST route %s failed: %s", mode, e)
        return {}


# ═══════════════════════════════════════════════════════════════
# MCP 响应解析
# ═══════════════════════════════════════════════════════════════

def _parse_mcp_pois(result: Any) -> list[dict[str, Any]]:
    """解析 MCP tool 返回的 POI 列表。

    MCP POI 格式: {pois: [{id, name, address, typecode, photo}]}
    — 不含 location/distance/rating，需后续 REST 增强。
    """
    import json
    items = []
    if isinstance(result, list):
        for item in result:
            if hasattr(item, "text") and item.text:
                try:
                    data = json.loads(item.text)
                    if isinstance(data, dict):
                        # MCP around_search: {"pois": [...]}
                        pois = data.get("pois", [data])
                        items.extend(pois if isinstance(pois, list) else [pois])
                    elif isinstance(data, list):
                        items.extend(data)
                except (json.JSONDecodeError, TypeError):
                    continue
    # 转为内部 POI 格式
    return [_mcp_poi_to_internal(p) for p in items if isinstance(p, dict)]


def _mcp_poi_to_internal(poi: dict[str, Any]) -> dict[str, Any]:
    """MCP POI → 内部格式（基础字段，后续 REST 增强）。"""
    return {
        "id": poi.get("id", ""),
        "name": poi.get("name", ""),
        "type": _infer_type(poi.get("type", ""), poi.get("typecode", "")),
        "lat": 0.0,
        "lng": 0.0,
        "address": poi.get("address", ""),
        "tel": "",
        "rating": 4.0,
        "avg_price": 0,
        "tags": [],
        "open_time": "",
        "business_area": "",
        "photos": [poi.get("photo")] if poi.get("photo") else [],
        "distance_km": 0,
        "child_friendly": _is_child_friendly(poi),
    }


def _parse_mcp_first_item(result: Any) -> dict[str, Any] | None:
    """解析 MCP 返回的第一个文本项为 dict。"""
    import json
    if isinstance(result, list):
        for item in result:
            if hasattr(item, "text") and item.text:
                try:
                    data = json.loads(item.text)
                    if isinstance(data, dict):
                        return data
                except (json.JSONDecodeError, TypeError):
                    continue
    return None


# ═══════════════════════════════════════════════════════════════
# REST POI → 内部格式转换
# ═══════════════════════════════════════════════════════════════

def _rest_poi_to_internal(poi: dict[str, Any]) -> dict[str, Any]:
    """REST v5 API POI → 内部格式，兼容 scorer/composer。"""
    location = poi.get("location", "0,0")
    lng_str, lat_str = location.split(",") if "," in location else ("0", "0")
    lng, lat = float(lng_str), float(lat_str)

    biz = poi.get("business", {})
    navi = poi.get("navi", {})

    return {
        "id": poi.get("id", ""),
        "name": poi.get("name", ""),
        "type": _infer_type(poi.get("type", ""), poi.get("typecode", "")),
        "lat": lat,
        "lng": lng,
        "address": poi.get("address", ""),
        "tel": biz.get("tel", ""),
        "rating": float(biz.get("rating", 0) or 4.0),
        "avg_price": float(biz.get("cost", 0) or 0),
        "tags": _extract_tags(poi),
        "open_time": biz.get("opentime_today", ""),
        "business_area": biz.get("business_area", ""),
        "photos": [p.get("url") for p in poi.get("photos", [])],
        "distance_km": round(float(poi.get("distance", 0)) / 1000, 2),
        "child_friendly": _is_child_friendly(poi),
        "navi_poiid": navi.get("navi_poiid", ""),
        "entr_location": navi.get("entr_location", ""),
        "children": [
            {
                "id": c.get("id", ""),
                "name": c.get("name", ""),
                "location": c.get("location", ""),
            }
            for c in poi.get("children", [])
        ],
    }


def _rest_regeo_poi(poi: dict[str, Any]) -> dict[str, Any]:
    """REST v3 逆地理编码返回的周边 POI。"""
    loc = poi.get("location", "0,0")
    lng_str, lat_str = loc.split(",") if "," in loc else ("0", "0")
    return {
        "id": poi.get("id", ""),
        "name": poi.get("name", ""),
        "type": poi.get("type", ""),
        "lng": float(lng_str),
        "lat": float(lat_str),
        "address": poi.get("address", ""),
        "distance_km": round(float(poi.get("distance", 0)) / 1000, 2),
        "business_area": poi.get("businessarea", ""),
        "tel": poi.get("tel", ""),
    }


def _merge_detail_fields(poi: dict[str, Any], detail: dict[str, Any]) -> None:
    """将 REST detail 的增强字段合并到已有 POI 中。

    MCP search 返回的 POI 不含 location/rating/cost 等增强字段，
    通过 REST v5/place/detail 批量补全。
    """
    biz = detail.get("business", {})
    if biz.get("rating"):
        poi["rating"] = float(biz["rating"])
    if biz.get("cost"):
        poi["avg_price"] = float(biz["cost"])
    if biz.get("tel"):
        poi["tel"] = biz["tel"]
    if biz.get("opentime_today"):
        poi["open_time"] = biz["opentime_today"]
    if biz.get("business_area"):
        poi["business_area"] = biz["business_area"]
    # 补全 MCP 缺失的 location (REST detail 返回 "lng,lat")
    loc = detail.get("location", "")
    if loc:
        parts = loc.split(",")
        if len(parts) == 2:
            poi["lng"] = float(parts[0])
            poi["lat"] = float(parts[1])
    if detail.get("photos"):
        poi["photos"] = [p.get("url") for p in detail["photos"]]
    if detail.get("children"):
        poi["children"] = [
            {"id": c.get("id", ""), "name": c.get("name", "")}
            for c in detail["children"]
        ]


# ═══════════════════════════════════════════════════════════════
# 类型推断 & 标签提取
# ═══════════════════════════════════════════════════════════════

# 高德 typecode 前缀 → 内部类型
_TYPECODE_MAP = {
    "05": "restaurant",   # 餐饮
    "06": "shopping",     # 购物
    "08": "entertainment", # 娱乐
    "11": "attraction",   # 景点
    "14": "museum",       # 科教
    "10": "hotel",        # 住宿
}

# 高德 type 关键词 → 内部类型
_TYPE_KEYWORD_MAP = {
    "餐厅": "restaurant", "餐饮": "restaurant", "火锅": "hotpot",
    "咖啡": "cafe", "酒吧": "bar",
    "公园": "park", "动物园": "zoo", "博物馆": "museum",
    "购物": "shopping", "商场": "shopping",
    "娱乐": "entertainment", "密室": "escape_room",
    "景点": "attraction", "风景": "attraction",
    "酒店": "hotel",
}


def _infer_type(poi_type: str, typecode: str) -> str:
    """从高德类型字段推断内部类型。"""
    # typecode 前缀匹配
    if typecode:
        for prefix, ptype in _TYPECODE_MAP.items():
            if typecode.startswith(prefix):
                return ptype
    # type 关键词匹配
    for kw, ptype in _TYPE_KEYWORD_MAP.items():
        if kw in poi_type:
            return ptype
    return "attraction"


def _extract_tags(poi: dict[str, Any]) -> list[str]:
    """从 POI 中提取标签。"""
    tags = []
    # 高德 type 字段: "餐饮服务;中餐厅;火锅"
    poi_type = poi.get("type", "")
    if poi_type:
        parts = poi_type.split(";")
        tags.extend(p for p in parts if p and len(p) < 10)

    # business.tag 特色标签（美食类）
    biz = poi.get("business", {})
    tag_str = biz.get("tag", "")
    if tag_str:
        tags.extend(t.strip() for t in tag_str.split(",") if t.strip())

    return list(dict.fromkeys(tags))  # 去重保序


def _is_child_friendly(poi: dict[str, Any]) -> bool:
    """推断是否亲子友好。"""
    name = poi.get("name", "")
    poi_type = poi.get("type", "")
    tags = _extract_tags(poi)
    text = name + poi_type + " ".join(tags)
    child_kw = ["亲子", "儿童", "家庭", "动物园", "博物馆", "科技馆", "公园"]
    return any(kw in text for kw in child_kw)


def _parse_districts(districts: list[dict]) -> list[dict[str, Any]]:
    """解析行政区划树。"""
    result = []
    for d in districts:
        item = {
            "adcode": d.get("adcode", ""),
            "name": d.get("name", ""),
            "citycode": d.get("citycode", ""),
            "level": d.get("level", ""),
            "center": d.get("center", ""),
            "children": _parse_districts(d.get("districts", [])),
        }
        result.append(item)
    return result


# ═══════════════════════════════════════════════════════════════
# Adapter singleton (DI via build_graph)
# ═══════════════════════════════════════════════════════════════

_adapter_singleton: AmapAdapter | None = None


def set_default_adapter(adapter: AmapAdapter) -> None:
    """注入 AmapAdapter 单例。由 build_graph 在启动时调用。"""
    global _adapter_singleton
    _adapter_singleton = adapter


def get_adapter() -> AmapAdapter:
    """获取 AmapAdapter 单例。首次调用时惰性创建默认实例。"""
    global _adapter_singleton
    if _adapter_singleton is None:
        _adapter_singleton = AmapAdapter()
    return _adapter_singleton
