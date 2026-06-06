"""
【前台商城路由汇总】— 注册所有前台端子路由

Author: SnapTrip Team
Date: 2026-05-26
"""

from fastapi import APIRouter

from app.api.portal.cart import router as cart_router
from app.api.portal.coupon import router as coupon_router
from app.api.portal.home import router as home_router
from app.api.portal.member import router as member_router
from app.api.portal.order import router as order_router
from app.api.portal.product import router as product_router

portal_router = APIRouter()

portal_router.include_router(home_router)
portal_router.include_router(product_router)
portal_router.include_router(cart_router)
portal_router.include_router(order_router)
portal_router.include_router(member_router)
portal_router.include_router(coupon_router)
