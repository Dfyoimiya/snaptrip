"""适配器包入口。"""

from marketplace.app.adapters.amap.district_adapter import AmapDistrictAdapter
from marketplace.app.adapters.amap.geocode_adapter import AmapGeocodeAdapter, AmapReGeocodeAdapter
from marketplace.app.adapters.amap.poi_adapter import AmapPoiAdapter
from marketplace.app.adapters.amap.route_adapter import AmapRouteAdapter

__all__ = [
    "AmapPoiAdapter",
    "AmapRouteAdapter",
    "AmapGeocodeAdapter",
    "AmapReGeocodeAdapter",
    "AmapDistrictAdapter",
]
