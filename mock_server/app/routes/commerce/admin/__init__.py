"""Mock Server — B端 admin routes package."""

from fastapi import APIRouter

from app.routes.commerce.admin import (
    auth_router,
    dashboard_router,
    employee_router,
    role_router,
    merchant_router,
    category_router,
    product_router,
    order_router,
    banner_router,
    notice_router,
    statistics_router,
    upload_router,
)

router = APIRouter(prefix="/api/admin/v1")

router.include_router(auth_router.router, tags=["管理端-认证"])
router.include_router(dashboard_router.router, tags=["管理端-仪表盘"])
router.include_router(employee_router.router, tags=["管理端-员工"])
router.include_router(role_router.router, tags=["管理端-角色"])
router.include_router(merchant_router.router, tags=["管理端-商家"])
router.include_router(category_router.router, tags=["管理端-分类"])
router.include_router(product_router.router, tags=["管理端-商品"])
router.include_router(order_router.router, tags=["管理端-订单"])
router.include_router(banner_router.router, tags=["管理端-营销-轮播图"])
router.include_router(notice_router.router, tags=["管理端-营销-公告"])
router.include_router(statistics_router.router, tags=["管理端-统计"])
router.include_router(upload_router.router, tags=["管理端-上传"])
