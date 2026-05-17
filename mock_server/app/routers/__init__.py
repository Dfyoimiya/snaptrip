"""Mock Server 路由集合。

Author: SnapTrip Team
Date: 2026-05-17
"""

from app.routers.delivery import router as delivery_router
from app.routers.order import router as order_router
from app.routers.poi import router as poi_router
from app.routers.queue import router as queue_router
from app.routers.route import router as route_router
from app.routers.weather import router as weather_router

__all__ = [
    "poi_router",
    "queue_router",
    "order_router",
    "route_router",
    "weather_router",
    "delivery_router",
]
