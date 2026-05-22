"""高德地理编码 / 逆地理编码响应 Schema —— Pydantic 模型。

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from marketplace.app.adapters.amap.schemas.types import AmapStr


class AmapGeoResult(BaseModel):
    """地理编码结果条目"""

    model_config = ConfigDict(extra="ignore")
    formatted_address: AmapStr = ""
    country: AmapStr = ""
    province: AmapStr = ""
    citycode: AmapStr = ""
    city: AmapStr = ""
    district: AmapStr = ""
    township: AmapStr = ""
    location: AmapStr = ""  # "经度,纬度"
    level: AmapStr = ""  # 匹配级别: 门牌号/小区/道路等
    building: dict | None = None


class AmapGeoResponse(BaseModel):
    """地理编码完整响应 (address → lng,lat)"""

    model_config = ConfigDict(extra="ignore")
    status: AmapStr = "0"
    infocode: AmapStr = ""
    info: AmapStr = ""
    count: AmapStr = "0"
    geocodes: list[AmapGeoResult] = Field(default_factory=list)


class AmapAddressComponent(BaseModel):
    """地址组件"""

    model_config = ConfigDict(extra="ignore")
    country: AmapStr = ""
    province: AmapStr = ""
    city: AmapStr = ""
    citycode: AmapStr = ""
    district: AmapStr = ""
    adcode: AmapStr = ""
    township: AmapStr = ""
    towncode: AmapStr = ""
    street_number: dict | None = None
    business_areas: list[dict] = Field(default_factory=list)


class AmapRegeoResult(BaseModel):
    """逆地理编码结果"""

    model_config = ConfigDict(extra="ignore")
    formatted_address: AmapStr = ""
    addressComponent: AmapAddressComponent = Field(default_factory=AmapAddressComponent)  # noqa: N815
    pois: list[dict] = Field(default_factory=list)
    roads: list[dict] = Field(default_factory=list)


class AmapRegeoResponse(BaseModel):
    """逆地理编码完整响应 (lng,lat → address)"""

    model_config = ConfigDict(extra="ignore")
    status: AmapStr = "0"
    infocode: AmapStr = ""
    info: AmapStr = ""
    regeocode: AmapRegeoResult = Field(default_factory=AmapRegeoResult)
