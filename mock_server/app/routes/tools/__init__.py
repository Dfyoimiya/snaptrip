"""Mock Server — tool routes package."""

from fastapi import APIRouter

from app.routes.tools import poi, order, route

router = APIRouter(prefix="/mock/tools")
router.include_router(poi.router, tags=["mock-tools-poi"])
router.include_router(order.router, tags=["mock-tools-order"])
router.include_router(route.router, tags=["mock-tools-route"])
