"""高德 Schema 包入口。"""

from marketplace.app.adapters.amap.schemas.district import AmapDistrictItem, AmapDistrictResponse
from marketplace.app.adapters.amap.schemas.geocode import (
    AmapGeoResponse,
    AmapGeoResult,
    AmapRegeoResponse,
    AmapRegeoResult,
)
from marketplace.app.adapters.amap.schemas.poi import AmapPoiItem, AmapPoiResponse
from marketplace.app.adapters.amap.schemas.route import AmapPath, AmapRouteResponse, AmapStep
from marketplace.app.adapters.amap.schemas.types import AmapStr
from marketplace.app.adapters.amap.schemas.weather import AmapLiveWeather, AmapWeatherResponse

__all__ = [
    "AmapStr",
    "AmapPoiItem",
    "AmapPoiResponse",
    "AmapPath",
    "AmapRouteResponse",
    "AmapStep",
    "AmapGeoResponse",
    "AmapGeoResult",
    "AmapRegeoResponse",
    "AmapRegeoResult",
    "AmapDistrictItem",
    "AmapDistrictResponse",
    "AmapLiveWeather",
    "AmapWeatherResponse",
]
