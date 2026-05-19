"""高德天气查询响应 Schema —— Pydantic 模型。

高德 API 文档: /v3/weather/weatherInfo  (city=110000)

响应结构:
  { "status": "1", "infocode": "10000",
    "lives": [{ "province": "北京", "city": "北京市",
               "weather": "晴", "temperature": "25", "winddirection": "北", ... }] }

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AmapLiveWeather(BaseModel):
    """实时天气数据"""

    province: str = ""
    city: str = ""
    adcode: str = ""
    weather: str = ""  # 天气现象: 晴/多云/雨等
    temperature: str = ""  # 摄氏度
    winddirection: str = ""  # 风向
    windpower: str = ""  # 风力级别
    humidity: str = ""  # 湿度百分比
    reporttime: str = ""  # 数据发布时间


class AmapWeatherResponse(BaseModel):
    """天气查询完整响应"""

    status: str = "0"
    infocode: str = ""
    info: str = ""
    count: str = "0"
    lives: list[AmapLiveWeather] = Field(default_factory=list)
    forecasts: list[dict] = Field(default_factory=list)  # 预报数据
