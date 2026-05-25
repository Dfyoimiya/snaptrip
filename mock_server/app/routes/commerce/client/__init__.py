"""Mock Server — commerce client routes package."""

from fastapi import APIRouter

from app.routes.commerce.client import (
    auth_router,
    user_router,
    home_router,
    merchant_router,
    product_router,
    cart_router,
    order_router,
    address_router,
    favorite_router,
    search_router,
    review_router,
)

router = APIRouter(prefix="/api/client/v1")

router.include_router(auth_router.router, tags=["客户端-认证"])
router.include_router(user_router.router, tags=["客户端-用户"])
router.include_router(home_router.router, tags=["客户端-首页"])
router.include_router(merchant_router.router, tags=["客户端-商家"])
router.include_router(product_router.router, tags=["客户端-商品"])
router.include_router(cart_router.router, tags=["客户端-购物车"])
router.include_router(order_router.router, tags=["客户端-订单"])
router.include_router(address_router.router, tags=["客户端-地址"])
router.include_router(favorite_router.router, tags=["客户端-收藏"])
router.include_router(search_router.router, tags=["客户端-搜索"])
router.include_router(review_router.router, tags=["客户端-评价"])
