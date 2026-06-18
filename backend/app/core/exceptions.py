"""电商业务异常 —— 继承 SnapTripException 统一异常体系。

层级:
  CommerceException (基类, 500)
  ├── ProductNotFoundError (404)
  ├── ProductOffShelfError (400)
  ├── InsufficientStockError (409)
  ├── OrderError (基类, 400)
  │   ├── OrderNotFoundError (404)
  │   ├── OrderStatusError (409)
  │   └── OrderPaymentError (402)
  ├── CouponError (基类, 400)
  │   ├── CouponExpiredError (400)
  │   └── CouponExhaustedError (409)
  └── CartError (基类, 400)

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from snaptrip_shared.core.exceptions import SnapTripException


class CommerceException(SnapTripException):
    """电商业务异常基类"""

    def __init__(self, code: str, message: str, status_code: int = 500, details: dict | None = None) -> None:
        super().__init__(code=code, message=message, status_code=status_code, details=details)


# ── 商品域 ──


class ProductNotFoundError(CommerceException):
    def __init__(self, product_id: str = "") -> None:
        super().__init__(
            code="PRODUCT_NOT_FOUND",
            message=f"商品不存在{f': {product_id}' if product_id else ''}",
            status_code=404,
        )


class ProductOffShelfError(CommerceException):
    def __init__(self, product_id: str = "") -> None:
        super().__init__(
            code="PRODUCT_OFF_SHELF",
            message=f"商品已下架{f': {product_id}' if product_id else ''}",
            status_code=400,
        )


class InsufficientStockError(CommerceException):
    def __init__(self, sku_id: str = "", available: int = 0, requested: int = 0) -> None:
        super().__init__(
            code="INSUFFICIENT_STOCK",
            message=f"库存不足: SKU {sku_id}, 可用 {available}, 请求 {requested}",
            status_code=409,
            details={"sku_id": sku_id, "available": available, "requested": requested},
        )


# ── 订单域 ──


class OrderError(CommerceException):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None) -> None:
        super().__init__(code=code, message=message, status_code=status_code, details=details)


class OrderNotFoundError(OrderError):
    def __init__(self, order_id: str = "") -> None:
        super().__init__(
            code="ORDER_NOT_FOUND",
            message=f"订单不存在{f': {order_id}' if order_id else ''}",
            status_code=404,
        )


class OrderStatusError(OrderError):
    def __init__(self, order_id: str = "", current_status: str = "", expected: str = "") -> None:
        super().__init__(
            code="ORDER_STATUS_ERROR",
            message=(
                f"订单状态不允许此操作{f': {order_id}' if order_id else ''}, 当前 {current_status}, 期望 {expected}"
            ),
            status_code=409,
        )


class OrderPaymentError(OrderError):
    def __init__(self, order_id: str = "", reason: str = "") -> None:
        super().__init__(
            code="ORDER_PAYMENT_ERROR",
            message=f"支付失败{f': {order_id}' if order_id else ''}{f' - {reason}' if reason else ''}",
            status_code=402,
        )


# ── 优惠券域 ──


class CouponError(CommerceException):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None) -> None:
        super().__init__(code=code, message=message, status_code=status_code, details=details)


class CouponExpiredError(CouponError):
    def __init__(self, coupon_id: str = "") -> None:
        super().__init__(
            code="COUPON_EXPIRED",
            message=f"优惠券已过期{f': {coupon_id}' if coupon_id else ''}",
            status_code=400,
        )


class CouponExhaustedError(CouponError):
    def __init__(self, coupon_id: str = "") -> None:
        super().__init__(
            code="COUPON_EXHAUSTED",
            message=f"优惠券已领完{f': {coupon_id}' if coupon_id else ''}",
            status_code=409,
        )


class CouponAlreadyClaimedError(CouponError):
    def __init__(self, coupon_id: str = "") -> None:
        super().__init__(
            code="COUPON_ALREADY_CLAIMED",
            message=f"已领取过此优惠券{f': {coupon_id}' if coupon_id else ''}",
            status_code=409,
        )


# ── 购物车域 ──


class CartError(CommerceException):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None) -> None:
        super().__init__(code=code, message=message, status_code=status_code, details=details)
