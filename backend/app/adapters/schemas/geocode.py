"""高德地理编码 / 逆地理编码响应 Schema —— Pydantic 模型。

高德 API 文档:
  - 地理编码: /v3/geocode/geo  (address → lng,lat)
  - 逆地理编码: /v3/geocode/regeo  (lng,lat → address)

响应结构:
  地理编码:
    { "status": "1", "infocode": "10000", "count": "1",
      "geocodes": [{ "location": "116.397,39.908", "city": "北京市", ... }] }
  逆地理编码:
    { "status": "1", "infocode": "10000",
      "regeocode": { "formatted_address": "...", "addressComponent": {...} } }

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _coerce_to_str(v: Any) -> str:
    """高德 API 部分字段可能返回 [] (空数组) 而非空字符串, 统一转换为 ""。"""
    if isinstance(v, list):
        return ""
    return str(v) if v else ""


class AmapGeoResult(BaseModel):
    """地理编码结果条目"""

    formatted_address: str = ""
    country: str = ""
    province: str = ""
    citycode: str = ""
    city: str = ""
    district: str = ""
    township: str = ""
    location: str = ""  # "经度,纬度"
    level: str = ""  # 匹配级别: 门牌号/小区/道路等
    building: dict | None = None

    @field_validator("township", mode="before")
    @classmethod
    def coerce_township(cls, v: Any) -> str:
        return _coerce_to_str(v)

    @field_validator("citycode", mode="before")
    @classmethod
    def coerce_citycode(cls, v: Any) -> str:
        return _coerce_to_str(v)


class AmapGeoResponse(BaseModel):
    """地理编码完整响应 (address → lng,lat)"""

    status: str = "0"
    infocode: str = ""
    info: str = ""
    count: str = "0"
    geocodes: list[AmapGeoResult] = Field(default_factory=list)


class AmapAddressComponent(BaseModel):
    """地址组件"""

    country: str = ""
    province: str = ""
    city: str = ""
    citycode: str = ""
    district: str = ""
    adcode: str = ""
    township: str = ""
    towncode: str = ""
    street_number: dict | None = None
    business_areas: list[dict] = Field(default_factory=list)


class AmapRegeoResult(BaseModel):
    """逆地理编码结果"""

    formatted_address: str = ""
    addressComponent: AmapAddressComponent = Field(default_factory=AmapAddressComponent)
    pois: list[dict] = Field(default_factory=list)
    roads: list[dict] = Field(default_factory=list)


class AmapRegeoResponse(BaseModel):
    """逆地理编码完整响应 (lng,lat → address)"""

    status: str = "0"
    infocode: str = ""
    info: str = ""
    regeocode: AmapRegeoResult = Field(default_factory=AmapRegeoResult)
