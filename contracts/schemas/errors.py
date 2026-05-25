"""Unified error codes across all domains. Mock and Real use the same codes."""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel


class ErrorCode(IntEnum):
    # ── User (1xxx) ──
    USER_INVALID_PHONE = 1001
    USER_PHONE_EXISTS = 1002
    USER_WRONG_PASSWORD = 1003
    USER_ACCOUNT_DISABLED = 1004
    USER_TOKEN_EXPIRED = 1005
    USER_TOKEN_INVALID = 1006
    USER_PERMISSION_DENIED = 1007

    # ── Auth / Admin (11xx) ──
    AUTH_WRONG_CREDENTIALS = 1101
    AUTH_ROLE_NO_PERMISSION = 1102
    AUTH_ACCOUNT_DISABLED = 1103

    # ── Merchant (2xxx) ──
    MERCH_NOT_FOUND = 2001
    MERCH_CLOSED = 2002
    MERCH_AUDIT_REQUIRED = 2003

    # ── Product (21xx) ──
    PROD_NOT_FOUND = 2101
    PROD_OFF_SHELF = 2102
    PROD_STOCK_INSUFFICIENT = 2103
    PROD_SPEC_INVALID = 2104

    # ── Order (3xxx) ──
    ORDER_NOT_FOUND = 3001
    ORDER_STATUS_INVALID = 3002
    ORDER_TIMEOUT_CANCELLED = 3003
    ORDER_CART_EMPTY = 3004
    ORDER_PRICE_CHANGED = 3005
    ORDER_OUT_OF_RANGE = 3006

    # ── Payment (31xx) ──
    PAY_AMOUNT_MISMATCH = 3101
    PAY_GATEWAY_ERROR = 3102
    PAY_DUPLICATE = 3103
    PAY_REFUND_EXCEED = 3104

    # ── Cart (32xx) ──
    CART_CROSS_MERCHANT = 3201
    CART_ITEM_INVALID = 3202

    # ── Search (4xxx) ──
    SRCH_KEYWORD_EMPTY = 4001
    SRCH_KEYWORD_TOO_LONG = 4002

    # ── Address (5xxx) ──
    ADDR_NOT_FOUND = 5001
    ADDR_LIMIT_REACHED = 5002

    # ── Review (6xxx) ──
    REVW_INVALID_RATING = 6001
    REVW_ALREADY_EXISTS = 6002
    REVW_SENSITIVE_CONTENT = 6003

    # ── Coupon (7xxx) ──
    CPN_NOT_FOUND = 7001
    CPN_EXPIRED = 7002
    CPN_THRESHOLD_NOT_MET = 7003

    # ── Admin (8xxx) ──
    ADMIN_NO_PAGE_ACCESS = 8001
    ADMIN_NO_OP_PERMISSION = 8002
    ADMIN_CANNOT_DELETE_SELF = 8003

    # ── System (9xxx) ──
    SYS_INTERNAL_ERROR = 9001
    SYS_SERVICE_UNAVAILABLE = 9002
    SYS_RATE_LIMITED = 9003
    SYS_FILE_TOO_LARGE = 9004

    # ── File (91xx) ──
    FILE_TYPE_UNSUPPORTED = 9101
    FILE_UPLOAD_FAILED = 9102


# Human-readable mapping: code → (message, http_status)
ERROR_META: dict[ErrorCode, tuple[str, int]] = {
    # User
    ErrorCode.USER_INVALID_PHONE: ("手机号格式不正确", 400),
    ErrorCode.USER_PHONE_EXISTS: ("该手机号已注册", 409),
    ErrorCode.USER_WRONG_PASSWORD: ("密码错误", 401),
    ErrorCode.USER_ACCOUNT_DISABLED: ("账号已被禁用", 401),
    ErrorCode.USER_TOKEN_EXPIRED: ("Token 已过期", 401),
    ErrorCode.USER_TOKEN_INVALID: ("Token 无效", 401),
    ErrorCode.USER_PERMISSION_DENIED: ("无权限执行此操作", 403),
    # Auth
    ErrorCode.AUTH_WRONG_CREDENTIALS: ("用户名或密码错误", 401),
    ErrorCode.AUTH_ROLE_NO_PERMISSION: ("角色无此操作权限", 403),
    ErrorCode.AUTH_ACCOUNT_DISABLED: ("账号已被禁用", 403),
    # Merchant
    ErrorCode.MERCH_NOT_FOUND: ("商家不存在", 404),
    ErrorCode.MERCH_CLOSED: ("商家已暂停营业", 400),
    ErrorCode.MERCH_AUDIT_REQUIRED: ("商家审核未通过", 400),
    # Product
    ErrorCode.PROD_NOT_FOUND: ("商品不存在", 404),
    ErrorCode.PROD_OFF_SHELF: ("商品已下架", 400),
    ErrorCode.PROD_STOCK_INSUFFICIENT: ("库存不足", 400),
    ErrorCode.PROD_SPEC_INVALID: ("规格不存在", 400),
    # Order
    ErrorCode.ORDER_NOT_FOUND: ("订单不存在", 404),
    ErrorCode.ORDER_STATUS_INVALID: ("当前状态不允许此操作", 400),
    ErrorCode.ORDER_TIMEOUT_CANCELLED: ("订单已超时取消", 400),
    ErrorCode.ORDER_CART_EMPTY: ("购物车为空", 400),
    ErrorCode.ORDER_PRICE_CHANGED: ("商品价格已变更", 400),
    ErrorCode.ORDER_OUT_OF_RANGE: ("超出配送范围", 400),
    # Payment
    ErrorCode.PAY_AMOUNT_MISMATCH: ("支付金额不匹配", 402),
    ErrorCode.PAY_GATEWAY_ERROR: ("支付网关异常", 500),
    ErrorCode.PAY_DUPLICATE: ("订单已支付", 400),
    ErrorCode.PAY_REFUND_EXCEED: ("退款金额超过实付金额", 400),
    # Cart
    ErrorCode.CART_CROSS_MERCHANT: ("购物车商品所属商家不同", 400),
    ErrorCode.CART_ITEM_INVALID: ("商品已失效", 400),
    # Search
    ErrorCode.SRCH_KEYWORD_EMPTY: ("搜索关键词为空", 400),
    ErrorCode.SRCH_KEYWORD_TOO_LONG: ("搜索关键词过长", 400),
    # Address
    ErrorCode.ADDR_NOT_FOUND: ("地址不存在", 404),
    ErrorCode.ADDR_LIMIT_REACHED: ("最多添加20个地址", 400),
    # Review
    ErrorCode.REVW_INVALID_RATING: ("评分为1-5整数", 400),
    ErrorCode.REVW_ALREADY_EXISTS: ("该订单已评价", 403),
    ErrorCode.REVW_SENSITIVE_CONTENT: ("评价内容含敏感词", 400),
    # Coupon
    ErrorCode.CPN_NOT_FOUND: ("优惠券不存在", 404),
    ErrorCode.CPN_EXPIRED: ("优惠券已过期", 400),
    ErrorCode.CPN_THRESHOLD_NOT_MET: ("不满足使用门槛", 400),
    # Admin
    ErrorCode.ADMIN_NO_PAGE_ACCESS: ("无此页面访问权限", 403),
    ErrorCode.ADMIN_NO_OP_PERMISSION: ("无此操作权限", 403),
    ErrorCode.ADMIN_CANNOT_DELETE_SELF: ("不能删除自己", 400),
    # System
    ErrorCode.SYS_INTERNAL_ERROR: ("服务器内部错误", 500),
    ErrorCode.SYS_SERVICE_UNAVAILABLE: ("服务暂不可用", 503),
    ErrorCode.SYS_RATE_LIMITED: ("请求过于频繁", 429),
    ErrorCode.SYS_FILE_TOO_LARGE: ("上传文件过大", 413),
    # File
    ErrorCode.FILE_TYPE_UNSUPPORTED: ("不支持的文件类型", 400),
    ErrorCode.FILE_UPLOAD_FAILED: ("上传失败", 400),
}


class ErrorResponse(BaseModel):
    """Structured error detail in Result.data when code != 0."""

    code: int
    message: str
    details: dict | None = None
