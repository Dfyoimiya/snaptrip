"""高德行政区划查询响应 Schema —— Pydantic 模型。

高德 API 文档: /v3/config/district  (keywords=北京&subdistrict=1)

响应结构:
  { "status": "1", "infocode": "10000",
    "districts": [{ "name": "北京市", "adcode": "110000", "center": "116.407,39.904", ... }] }

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AmapDistrictItem(BaseModel):
    """行政区条目"""

    citycode: str = ""
    adcode: str = ""
    name: str = ""
    center: str = ""  # "经度,纬度"
    level: str = ""  # country/province/city/district
    districts: list[AmapDistrictItem] = Field(default_factory=list)  # type: ignore[name-defined]


class AmapDistrictResponse(BaseModel):
    """行政区划查询完整响应"""

    status: str = "0"
    infocode: str = ""
    info: str = ""
    count: str = "0"
    districts: list[AmapDistrictItem] = Field(default_factory=list)
