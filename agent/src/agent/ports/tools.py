"""工具端口 —— 地理位置服务抽象。

定义 Agent 所需的所有地理位置工具能力。
MCP 优先，REST API 降级。

Author: SnapTrip Team
Date: 2026-05-27
"""

from __future__ import annotations

from typing import Any, Protocol


class ToolPort(Protocol):
    """地理位置工具端口。

    所有方法均为异步，返回结构化 dict/list。
    实现者负责 MCP/REST 调用策略和格式转换。
    """

    # ── 搜索 ──────────────────────────────────────────────────

    async def search_pois_by_keyword(
        self,
        keywords: str,
        city: str = "",
        types: str = "",
        offset: int = 10,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """关键词搜索 POI。"""
        ...

    async def search_pois_around(
        self,
        location: str,
        radius: int = 5000,
        keywords: str = "",
        types: str = "",
        offset: int = 10,
    ) -> list[dict[str, Any]]:
        """周边搜索 POI。location="lng,lat"。"""
        ...

    async def get_poi_detail(self, poi_ids: list[str]) -> list[dict[str, Any]]:
        """批量获取 POI 详情（含增强字段）。"""
        ...

    async def input_tips(
        self,
        keywords: str,
        city: str = "",
        location: str = "",
    ) -> list[dict[str, Any]]:
        """输入提示 / 搜索自动补全。"""
        ...

    # ── 地理编码 ──────────────────────────────────────────────

    async def geocode(self, address: str, city: str = "") -> dict[str, Any]:
        """地理编码：地址 → 经纬度。返回 {lng, lat, adcode, ...}。"""
        ...

    async def reverse_geocode(
        self,
        location: str,
        radius: int = 1000,
        with_pois: bool = False,
    ) -> dict[str, Any]:
        """逆地理编码：经纬度 → 地址 + 周边 POI。"""
        ...

    async def ip_location(self, ip: str = "") -> dict[str, Any]:
        """IP 定位。返回 {province, city, adcode, location}。"""
        ...

    async def get_district(
        self,
        keywords: str,
        subdistrict: int = 1,
    ) -> list[dict[str, Any]]:
        """行政区域查询。返回省市区 adcode/citycode/center。"""
        ...

    # ── 天气 ──────────────────────────────────────────────────

    async def get_weather(
        self,
        city_adcode: str,
        forecast: bool = False,
    ) -> dict[str, Any]:
        """天气查询。forecast=False 返回实况，True 返回预报。"""
        ...

    # ── 路径规划 ──────────────────────────────────────────────

    async def estimate_travel_time(
        self,
        origin: str,
        destination: str,
        mode: str = "driving",
    ) -> dict[str, Any]:
        """估算两点间行程距离和时间。返回 {distance_km, duration_min}。"""
        ...

    async def get_route_plan(
        self,
        origin: str,
        destination: str,
        mode: str = "driving",
        strategy: int = 32,
        city1: str = "",
        city2: str = "",
    ) -> dict[str, Any]:
        """路径规划。返回 {distance, duration, steps, polyline, taxi_cost}。"""
        ...

    # ── MCP 专属 ──────────────────────────────────────────────

    async def generate_custom_map(
        self,
        title: str,
        daily_schedules: list[dict[str, Any]],
    ) -> str:
        """生成高德专属地图，返回唤端链接。"""
        ...

    async def navigate_to_destination(self, location: str) -> str:
        """导航到目的地，返回导航唤端链接。"""
        ...

    async def hail_ride(self, origin: str, destination: str) -> str:
        """发起打车，返回高德打车唤端链接。"""
        ...
