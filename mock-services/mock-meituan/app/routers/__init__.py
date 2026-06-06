"""Mock Server 路由集合。

Author: SnapTrip Team
Date: 2026-05-30
"""

from app.routers.delivery import router as delivery_router
from app.routers.hotel import router as hotel_router
from app.routers.leisure import router as leisure_router
from app.routers.movie import router as movie_router
from app.routers.order import router as order_router
from app.routers.poi import router as poi_router
from app.routers.reservation import router as reservation_router
from app.routers.route import router as route_router
from app.routers.takeout import router as takeout_router
from app.routers.weather import router as weather_router

__all__ = [
    "poi_router",
    "order_router",
    "route_router",
    "weather_router",
    "delivery_router",
    "reservation_router",
    "takeout_router",
    "movie_router",
    "hotel_router",
    "leisure_router",
]
