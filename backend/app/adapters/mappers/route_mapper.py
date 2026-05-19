"""Route Mapper —— 高德 AmapPath → 内部路由数据。

映射规则:
  AmapPath:
    distance ("1500" 米)  → distance_km
    duration ("900" 秒)   → duration_min
    steps[].polyline      → polyline (用于地图绘制)

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from app.adapters.schemas.route import AmapPath


class RouteMapper:
    """高德路径 → 内部路由数据转换器。"""

    @staticmethod
    def to_internal(path: AmapPath) -> dict:
        """将高德路径方案转换为内部路由数据。

        Args:
            path: 高德路径方案

        Returns:
            dict 含 distance_km / duration_min / polyline / steps
        """
        distance_m = 0
        if path.distance:
            try:
                distance_m = int(path.distance)
            except (ValueError, TypeError):
                pass

        duration_s = 0
        if path.duration:
            try:
                duration_s = int(path.duration)
            except (ValueError, TypeError):
                pass

        polyline = ""
        if path.steps:
            polyline_parts = [s.polyline for s in path.steps if s.polyline]
            polyline = ";".join(polyline_parts)

        return {
            "distance_km": round(distance_m / 1000.0, 2),
            "distance_m": distance_m,
            "duration_min": max(1, round(duration_s / 60.0)),
            "tolls": path.tolls,
            "traffic_lights": path.traffic_lights,
            "polyline": polyline,
            "step_count": len(path.steps),
        }

    @staticmethod
    def to_route_summary(paths: list[AmapPath]) -> dict:
        """从多条路径方案中提取最短路径摘要。

        Args:
            paths: 路径方案列表

        Returns:
            dict: 最短路径的摘要信息
        """
        if not paths:
            return {"distance_km": 0, "duration_min": 0}

        shortest = min(paths, key=lambda p: int(p.duration) if p.duration else 0)
        return RouteMapper.to_internal(shortest)
