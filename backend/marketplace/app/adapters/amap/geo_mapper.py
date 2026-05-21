"""Geo Mapper —— 坐标/地址转换工具。

职责:
  - 解析高德 location 字符串 ("116.397,39.908") → (lat, lng)
  - 格式化坐标 → "lng,lat" (高德 API 输入格式)
  - 经纬度校验

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations


class GeoMapper:
    """坐标转换工具函数集合。"""

    @staticmethod
    def parse_location(location: str) -> tuple[float, float]:
        """高德 location 字符串 → (lat, lng)。

        Args:
            location: "116.397,39.908" 格式 (经度,纬度)

        Returns:
            (lat, lng) 元组, 解析失败返回 (0.0, 0.0)
        """
        if not location or "," not in location:
            return 0.0, 0.0
        try:
            lng_str, lat_str = location.split(",", 1)
            return float(lat_str), float(lng_str)
        except (ValueError, IndexError):
            return 0.0, 0.0

    @staticmethod
    def format_location(lat: float, lng: float) -> str:
        """格式化坐标为高德 API 输入格式 "lng,lat"。

        Args:
            lat: 纬度
            lng: 经度

        Returns:
            "116.397,39.908" 格式字符串
        """
        return f"{lng:.6f},{lat:.6f}"

    @staticmethod
    def is_valid_coordinate(lat: float, lng: float) -> bool:
        """校验经纬度是否在合法范围内。

        Args:
            lat: 纬度 (-90 ~ 90)
            lng: 经度 (-180 ~ 180)

        Returns:
            True 表示合法坐标
        """
        return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0

    @staticmethod
    def build_origin_dest(
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
    ) -> tuple[str, str]:
        """构建高德 API 所需的起终点参数。

        Args:
            from_lat/from_lng: 起点坐标
            to_lat/to_lng: 终点坐标

        Returns:
            (origin, destination) 字符串元组
        """
        return (
            GeoMapper.format_location(from_lat, from_lng),
            GeoMapper.format_location(to_lat, to_lng),
        )
