"""Shared enumerations used across all domains."""

from __future__ import annotations

from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "PENDING"           # 待支付
    PAID = "PAID"                 # 已支付
    CONFIRMED = "CONFIRMED"       # 已接单
    DELIVERING = "DELIVERING"     # 配送中
    COMPLETED = "COMPLETED"       # 已完成
    CANCELLED = "CANCELLED"       # 已取消


class PayStatus(str, Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    REFUNDING = "REFUNDING"
    REFUNDED = "REFUNDED"


class MerchantStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RESTING = "RESTING"


class AuditStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProductStatus(str, Enum):
    ON_SHELF = "ON_SHELF"
    OFF_SHELF = "OFF_SHELF"


class RoleCode(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    MERCHANT_MANAGER = "MERCHANT_MANAGER"
    ORDER_STAFF = "ORDER_STAFF"


class BannerPosition(str, Enum):
    HOME_TOP = "HOME_TOP"
    HOME_MIDDLE = "HOME_MIDDLE"


class NoticeTargetType(str, Enum):
    ALL = "ALL"
    CUSTOMER = "CUSTOMER"
    MERCHANT = "MERCHANT"


class FavoriteTargetType(str, Enum):
    PRODUCT = "product"
    MERCHANT = "merchant"


class CategoryType(str, Enum):
    PRODUCT = "PRODUCT"
    COMBO = "COMBO"
