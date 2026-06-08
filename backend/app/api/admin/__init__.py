"""
【后台管理路由汇总】— 注册所有管理端子路由

Author: SnapTrip Team
Date: 2026-05-26
"""

from fastapi import APIRouter

from app.api.admin.attribute import router as attribute_router
from app.api.admin.brand import router as brand_router
from app.api.admin.category import router as category_router
from app.api.admin.cms import cms_router, stats_router
from app.api.admin.coupon import router as coupon_router
from app.api.admin.dashboard import router as dashboard_router
from app.api.admin.flash import router as flash_router
from app.api.admin.member import router as member_router
from app.api.admin.order import router as order_router
from app.api.admin.product import router as product_router

admin_router = APIRouter()

admin_router.include_router(category_router)
admin_router.include_router(brand_router)
admin_router.include_router(attribute_router)
admin_router.include_router(product_router)
admin_router.include_router(order_router)
admin_router.include_router(member_router)
admin_router.include_router(coupon_router)
admin_router.include_router(dashboard_router)
admin_router.include_router(flash_router)
admin_router.include_router(cms_router)
admin_router.include_router(stats_router)
