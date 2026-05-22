"""高德天气查询响应 Schema —— Pydantic 模型。

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from marketplace.app.adapters.amap.schemas.types import AmapStr


class AmapLiveWeather(BaseModel):
    """实时天气数据"""

    model_config = ConfigDict(extra="ignore")
    province: AmapStr = ""
    city: AmapStr = ""
    adcode: AmapStr = ""
    weather: AmapStr = ""  # 天气现象: 晴/多云/雨等
    temperature: AmapStr = ""  # 摄氏度
    winddirection: AmapStr = ""  # 风向
    windpower: AmapStr = ""  # 风力级别
    humidity: AmapStr = ""  # 湿度百分比
    reporttime: AmapStr = ""  # 数据发布时间


class AmapWeatherResponse(BaseModel):
    """天气查询完整响应"""

    model_config = ConfigDict(extra="ignore")
    status: AmapStr = "0"
    infocode: AmapStr = ""
    info: AmapStr = ""
    count: AmapStr = "0"
    lives: list[AmapLiveWeather] = Field(default_factory=list)
    forecasts: list[dict] = Field(default_factory=list)  # 预报数据
