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

# ── UMS / RBAC (Phase 6) ──
from app.api.admin.menu import router as menu_router
from app.api.admin.resource import rcat_router, res_router
from app.api.admin.role import router as role_router
from app.api.admin.ums_admin import router as ums_admin_router

# ── Macalline Compatibility ──
from app.api.admin.product_category_compat import router as product_category_router
from app.api.admin.product_attribute_compat import router as product_attribute_router
from app.api.admin.home_compat import router as home_router
from app.api.admin.misc_compat import (
    company_address_router,
    order_setting_router,
    oss_router,
    prefrence_area_router,
    return_apply_router,
    return_reason_router,
    sku_router,
    subject_router,
)

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

# ── UMS / RBAC ──
admin_router.include_router(menu_router)
admin_router.include_router(rcat_router)
admin_router.include_router(res_router)
admin_router.include_router(role_router)
admin_router.include_router(ums_admin_router)

# ── Macalline Compatibility ──
admin_router.include_router(product_category_router)
admin_router.include_router(product_attribute_router)
admin_router.include_router(home_router)
admin_router.include_router(subject_router)
admin_router.include_router(sku_router)
admin_router.include_router(order_setting_router)
admin_router.include_router(return_apply_router)
admin_router.include_router(return_reason_router)
admin_router.include_router(company_address_router)
admin_router.include_router(oss_router)
admin_router.include_router(prefrence_area_router)
