"""适配器包入口。"""

from app.adapters.adapters.district_adapter import AmapDistrictAdapter
from app.adapters.adapters.geocode_adapter import AmapGeocodeAdapter, AmapReGeocodeAdapter
from app.adapters.adapters.poi_adapter import AmapPoiAdapter
from app.adapters.adapters.route_adapter import AmapRouteAdapter

__all__ = [
    "AmapPoiAdapter",
    "AmapRouteAdapter",
    "AmapGeocodeAdapter",
    "AmapReGeocodeAdapter",
    "AmapDistrictAdapter",
]
