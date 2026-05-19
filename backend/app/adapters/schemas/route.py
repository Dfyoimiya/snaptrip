"""高德路径规划响应 Schema —— Pydantic 模型。

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.adapters.schemas.types import AmapStr


class AmapStep(BaseModel):
    """路径导航步骤"""

    model_config = ConfigDict(extra="ignore")
    instruction: AmapStr = ""
    orientation: AmapStr = ""
    road: AmapStr = ""
    distance: AmapStr = ""  # 米
    duration: AmapStr = ""  # 秒
    polyline: AmapStr = ""
    action: AmapStr = ""
    assistant_action: AmapStr = ""


class AmapPath(BaseModel):
    """路径方案"""

    model_config = ConfigDict(extra="ignore")
    distance: AmapStr = ""  # 总距离 (米)
    duration: AmapStr = ""  # 总时间 (秒)
    steps: list[AmapStep] = Field(default_factory=list)
    tolls: AmapStr = "0"  # 过路费
    restriction: AmapStr = ""
    traffic_lights: AmapStr = "0"


class AmapRouteScheme(BaseModel):
    """路径规划返回的路线"""

    model_config = ConfigDict(extra="ignore")
    paths: list[AmapPath] = Field(default_factory=list)
    origin: AmapStr = ""
    destination: AmapStr = ""


class AmapRouteResponse(BaseModel):
    """高德路径规划完整响应"""

    model_config = ConfigDict(extra="ignore")
    status: AmapStr = "0"
    infocode: AmapStr = ""
    info: AmapStr = ""
    count: AmapStr = "0"
    route: AmapRouteScheme = Field(default_factory=AmapRouteScheme)
