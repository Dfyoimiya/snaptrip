"""高德 POI 搜索响应 Schema —— Pydantic 模型。

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.adapters.schemas.types import AmapStr


class AmapPoiPhoto(BaseModel):
    """POI 图片"""

    model_config = ConfigDict(extra="ignore")
    url: str = ""
    title: AmapStr = ""


class AmapPoiBizExt(BaseModel):
    """POI 商业扩展信息"""

    model_config = ConfigDict(extra="ignore")
    rating: AmapStr | None = None
    cost: AmapStr | None = None
    open_time: AmapStr | None = None


class AmapPoiItem(BaseModel):
    """高德 POI 条目"""

    model_config = ConfigDict(extra="ignore")
    id: AmapStr = ""
    name: AmapStr = ""
    type: AmapStr = ""
    typecode: AmapStr = ""
    address: AmapStr = ""
    location: AmapStr = ""  # "经度,纬度"
    pname: AmapStr = ""  # 省
    cityname: AmapStr = ""
    adname: AmapStr = ""  # 区/县
    business_area: AmapStr = ""
    tel: AmapStr | None = None
    photos: list[AmapPoiPhoto] = Field(default_factory=list)
    distance: AmapStr | None = None  # 距中心点距离 (米)
    biz_ext: AmapPoiBizExt | None = None
    indoor_map: bool = False
    navi_poi_id: AmapStr | None = None


class AmapPoiResponse(BaseModel):
    """高德 POI 搜索完整响应"""

    model_config = ConfigDict(extra="ignore")
    status: AmapStr = "0"
    infocode: AmapStr = ""
    info: AmapStr = ""
    count: AmapStr = "0"
    pois: list[AmapPoiItem] = Field(default_factory=list)
    suggestion: dict | None = None
