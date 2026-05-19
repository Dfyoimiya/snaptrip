"""高德路径规划响应 Schema —— Pydantic 模型。

高德 API 文档:
  - 驾车: /v3/direction/driving  (origin + destination)
  - 步行: /v3/direction/walking
  - 公交: /v3/direction/transit
  - 骑行: /v3/direction/bicycling

响应结构:
  {
    "status": "1", "infocode": "10000",
    "route": {
      "paths": [{
        "distance": "1500", "duration": "900",
        "steps": [{ "instruction": "...", "road": "...", "distance": "300", ... }]
      }]
    }
  }

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AmapStep(BaseModel):
    """路径导航步骤"""

    instruction: str = ""
    orientation: str = ""
    road: str = ""
    distance: str = ""  # 米
    duration: str = ""  # 秒
    polyline: str = ""
    action: str = ""
    assistant_action: str = ""


class AmapPath(BaseModel):
    """路径方案"""

    distance: str = ""  # 总距离 (米)
    duration: str = ""  # 总时间 (秒)
    steps: list[AmapStep] = Field(default_factory=list)
    tolls: str = "0"  # 过路费
    restriction: str = ""
    traffic_lights: str = "0"


class AmapRouteScheme(BaseModel):
    """路径规划返回的路线"""

    paths: list[AmapPath] = Field(default_factory=list)
    origin: str = ""
    destination: str = ""


class AmapRouteResponse(BaseModel):
    """高德路径规划完整响应"""

    status: str = "0"
    infocode: str = ""
    info: str = ""
    count: str = "0"
    route: AmapRouteScheme = Field(default_factory=AmapRouteScheme)
