"""POI Mapper —— 高德 AmapPoiItem → 内部 POI Schema。

映射规则:
  AmapPoiItem:
    id          → POI.id          (高德 POI ID)
    name        → POI.name        (直接映射)
    location    → POI.lat/lng     (拆分 "经度,纬度" 字符串)
    address     → POI 扩展字段    (通过 metadata 传递)
    cityname    → POI.city        (直接映射)
    typecode    → POI.type        (高德分类码 → POIType 映射表)
    biz_ext     → POI.avg_price + rating
    distance    → 辅助排序用

分类码映射规则 (高德三位分类码):
  05xxxx → restaurant (餐饮)
  06xxxx → shopping   (购物)
  08xxxx → sports     (体育休闲)
  09xxxx → media      (传媒)
  10xxxx → hotel      (住宿)
  11xxxx → scenery    (风景名胜)
  14xxxx → education  (科教文化)
  其他    → attraction (默认)

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

import contextlib

from snaptrip_shared.schemas.plan import POI

from marketplace.app.adapters.amap.schemas.poi import AmapPoiItem

AMAP_TYPE_MAP: dict[str, str] = {
    "05": "restaurant",
    "06": "shopping",
    "07": "life_service",
    "08": "sports",
    "09": "media",
    "10": "hotel",
    "11": "scenery",
    "12": "healthcare",
    "13": "government",
    "14": "education",
    "15": "transportation",
    "16": "finance",
    "17": "enterprise",
    "18": "public",
    "19": "accommodation",
    "20": "storage",
}


def _parse_location(location: str) -> tuple[float, float]:
    """解析高德坐标字符串 "经度,纬度" → (lat, lng)。

    Args:
        location: "116.397,39.908" 格式

    Returns:
        (lat, lng) 元组, 解析失败返回 (0.0, 0.0)
    """
    if not location or "," not in location:
        return 0.0, 0.0
    try:
        parts = location.split(",", 1)
        return float(parts[1]), float(parts[0])
    except (ValueError, IndexError):
        return 0.0, 0.0


def _map_typecode_to_poi_type(typecode: str) -> str:
    """高德三位分类码 → 内部 POI 类型。

    高德分类码格式为 6位: 前3位=大类, 中3位=中类, 后3位=小类。
    我们取前2位作为大类映射键。
    """
    if not typecode:
        return "attraction"
    category = typecode[:2]
    return AMAP_TYPE_MAP.get(category, "attraction")


def _parse_mood_tags(name: str, typecode: str) -> list[str]:
    """根据 POI 名称和类型推断 mood_tags。

    简单规则: 餐饮类 → ["聚餐"], 风景类 → ["拍照","户外"],
    咖啡馆 → ["安静","治愈"], 体育 → ["运动","活力"]
    """
    mapped_type = _map_typecode_to_poi_type(typecode)
    tags_by_type: dict[str, list[str]] = {
        "restaurant": ["聚餐", "美食"],
        "shopping": ["逛街", "时尚"],
        "sports": ["运动", "活力"],
        "scenery": ["拍照", "户外"],
        "education": ["文艺", "安静"],
        "hotel": ["舒适", "享受"],
    }
    return tags_by_type.get(mapped_type, ["休闲"])


class PoiMapper:
    """高德 POI → 内部 POI Schema 转换器。

    纯函数, 无副作用, 可独立单元测试。
    """

    @staticmethod
    def to_internal(amap_poi: AmapPoiItem, city_override: str = "") -> POI:
        """将高德 POI 条目转换为内部 POI Schema。

        Args:
            amap_poi: 高德 POI 条目
            city_override: 城市覆盖 (当 API 未返回 cityname 时使用)

        Returns:
            POI: 内部 Schema 对象
        """
        lat, lng = _parse_location(amap_poi.location)
        city = amap_poi.cityname or city_override
        poi_type = _map_typecode_to_poi_type(amap_poi.typecode)

        avg_price = 0
        rating = 0.0
        business_hours = "09:00-22:00"
        if amap_poi.biz_ext:
            if amap_poi.biz_ext.cost:
                with contextlib.suppress(ValueError, TypeError):
                    avg_price = int(float(amap_poi.biz_ext.cost))
            if amap_poi.biz_ext.rating:
                with contextlib.suppress(ValueError, TypeError):
                    rating = float(amap_poi.biz_ext.rating)
            if amap_poi.biz_ext.open_time:
                business_hours = amap_poi.biz_ext.open_time

        mood_tags = _parse_mood_tags(amap_poi.name, amap_poi.typecode)

        return POI(
            id=amap_poi.id,
            name=amap_poi.name,
            city=city,
            type=poi_type,
            lat=lat,
            lng=lng,
            mood_tags=mood_tags,
            avg_price=avg_price,
            rating=rating,
            business_hours=business_hours,
        )

    @staticmethod
    def to_internal_batch(amap_pois: list[AmapPoiItem], city_override: str = "") -> list[POI]:
        """批量转换。

        Args:
            amap_pois: 高德 POI 列表
            city_override: 统一的 city 覆盖

        Returns:
            内部 POI 列表
        """
        return [PoiMapper.to_internal(p, city_override) for p in amap_pois]
