"""高德行政区划查询响应 Schema —— Pydantic 模型。

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.adapters.schemas.types import AmapStr


class AmapDistrictItem(BaseModel):
    """行政区条目"""

    model_config = ConfigDict(extra="ignore")
    citycode: AmapStr = ""
    adcode: AmapStr = ""
    name: AmapStr = ""
    center: AmapStr = ""  # "经度,纬度"
    level: AmapStr = ""  # country/province/city/district
    districts: list[AmapDistrictItem] = Field(default_factory=list)  # type: ignore[name-defined]


class AmapDistrictResponse(BaseModel):
    """行政区划查询完整响应"""

    model_config = ConfigDict(extra="ignore")
    status: AmapStr = "0"
    infocode: AmapStr = ""
    info: AmapStr = ""
    count: AmapStr = "0"
    districts: list[AmapDistrictItem] = Field(default_factory=list)
