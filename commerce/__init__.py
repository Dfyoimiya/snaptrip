"""SnapTrip Commerce API — shared across mock_server and backend."""

from commerce.routers.client import router as client_router
from commerce.routers.admin import router as admin_router

__all__ = ["client_router", "admin_router"]
