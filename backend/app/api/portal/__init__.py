"""
【前台商城路由汇总】— 注册所有前台端子路由

Author: SnapTrip Team
Date: 2026-05-26
"""

from fastapi import APIRouter

from app.api.portal.behavior import router as behavior_router
from app.api.portal.brand import router as brand_router
from app.api.portal.cart import router as cart_router
from app.api.portal.category import router as category_router
from app.api.portal.coupon import router as coupon_router
from app.api.portal.customer_service import router as cs_router
from app.api.portal.flash import router as flash_router
from app.api.portal.home import router as home_router
from app.api.portal.homefeed import router as homefeed_router
from app.api.portal.images import router as images_router
from app.api.portal.member import router as member_router
from app.api.portal.notice import router as notice_router
from app.api.portal.order import router as order_router
from app.api.portal.product import router as product_router
from app.api.portal.recommendation import router as recommendation_router
from app.api.portal.review import router as review_router
from app.api.portal.search_suggest import router as search_suggest_router
from app.api.portal.shopping_guide import router as shopping_guide_router

portal_router = APIRouter()

portal_router.include_router(images_router)
portal_router.include_router(review_router)
portal_router.include_router(shopping_guide_router)
portal_router.include_router(cs_router)
portal_router.include_router(recommendation_router)
portal_router.include_router(search_suggest_router)
portal_router.include_router(behavior_router)
portal_router.include_router(home_router)
portal_router.include_router(homefeed_router)
portal_router.include_router(product_router)
portal_router.include_router(cart_router)
portal_router.include_router(order_router)
portal_router.include_router(member_router)
portal_router.include_router(coupon_router)
portal_router.include_router(brand_router)
portal_router.include_router(category_router)
portal_router.include_router(notice_router)
portal_router.include_router(flash_router)
