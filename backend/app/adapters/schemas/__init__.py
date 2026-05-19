"""高德 Schema 包入口。"""

from app.adapters.schemas.district import AmapDistrictItem, AmapDistrictResponse
from app.adapters.schemas.geocode import AmapGeoResponse, AmapGeoResult, AmapRegeoResponse, AmapRegeoResult
from app.adapters.schemas.poi import AmapPoiItem, AmapPoiResponse
from app.adapters.schemas.route import AmapPath, AmapRouteResponse, AmapStep
from app.adapters.schemas.types import AmapStr
from app.adapters.schemas.weather import AmapLiveWeather, AmapWeatherResponse

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
