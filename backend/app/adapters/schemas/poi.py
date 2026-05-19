"""高德 POI 搜索响应 Schema —— Pydantic 模型。

高德 API 文档:
  - 周边搜索: /v3/place/around  (lat/lng + radius)
  - 关键字搜索: /v3/place/text  (keywords + city)
  - POI 详情: /v3/place/detail  (id)

响应结构:
  {
    "status": "1", "infocode": "10000", "count": "10",
    "pois": [{ "id": "B000A7BD6C", "name": "故宫", "location": "116.397,39.908", ... }]
  }

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AmapPoiPhoto(BaseModel):
    """POI 图片"""

    url: str = ""
    title: str = ""


class AmapPoiBizExt(BaseModel):
    """POI 商业扩展信息"""

    rating: str | None = None
    cost: str | None = None
    open_time: str | None = None


class AmapPoiItem(BaseModel):
    """高德 POI 条目"""

    id: str = ""
    name: str = ""
    type: str = ""
    typecode: str = ""
    address: str = ""
    location: str = ""  # "经度,纬度"
    pname: str = ""  # 省
    cityname: str = ""
    adname: str = ""  # 区/县
    business_area: str = ""
    tel: str | None = None
    photos: list[AmapPoiPhoto] = Field(default_factory=list)
    distance: str | None = None  # 距中心点距离 (米)
    biz_ext: AmapPoiBizExt | None = None
    indoor_map: bool = False
    navi_poi_id: str | None = None


class AmapPoiResponse(BaseModel):
    """高德 POI 搜索完整响应"""

    status: str = "0"
    infocode: str = ""
    info: str = ""
    count: str = "0"
    pois: list[AmapPoiItem] = Field(default_factory=list)
    suggestion: dict | None = None
