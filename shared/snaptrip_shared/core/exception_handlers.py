"""全局异常处理器 —— 将所有业务异常统一转换为 API 响应。

每个异常类型注册独立的 FastAPI exception_handler:
- SnapTripException 子类按 status_code + code 转换
- 未知 Exception 返回 500 并隐藏内部细节
- 所有异常经结构化日志记录，含 trace_id 关联

映射规则:
  - AdapterError / AmapApiError / AmapRateLimitError → 502, degraded
  - CircuitBreakerOpenError → 503, 保留降级标记
  - ValidationError → 422, 字段级错误信息
  - 未知 Exception → 500, 仅暴露 "Internal Server Error"

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

import traceback
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from snaptrip_shared.core.exceptions import (
    AdapterError,
    AmapRateLimitError,
    AuthenticationError,
    CircuitBreakerOpenError,
    PermissionDeniedError,
    ResourceNotFoundError,
    SnapTripException,
    ValidationError,
)
from snaptrip_shared.core.logging import get_logger

logger = get_logger(__name__)


def _make_response(
    exc: SnapTripException,
    trace_id: str,
    include_details: bool = True,
) -> JSONResponse:
    """构建统一异常响应体。

    Args:
        exc: 业务异常实例
        trace_id: 关联日志的 trace_id
        include_details: 是否在响应中携带 details

    Returns:
        JSONResponse 含 {code, message, data, error}
    """
    body: dict = {
        "code": -abs(exc.status_code),
        "message": exc.message,
        "data": None,
        "error": {
            "error_code": exc.code,
            "trace_id": trace_id,
        },
    }
    if include_details and exc.details:
        body["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=body)


async def snap_trip_exception_handler(request: Request, exc: SnapTripException) -> JSONResponse:
    """兜底: 所有 SnapTripException 子类统一处理。"""
    trace_id = str(uuid.uuid4())[:12]
    logger.error(
        "snaptrip_exception",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        trace_id=trace_id,
    )
    return _make_response(exc, trace_id)


async def adapter_exception_handler(request: Request, exc: AdapterError) -> JSONResponse:
    """高德 API 适配异常 —— 标记为外部服务降级。"""
    trace_id = str(uuid.uuid4())[:12]
    logger.error(
        "adapter_exception",
        code=exc.code,
        message=exc.message,
        path=request.url.path,
        trace_id=trace_id,
        details=exc.details,
    )
    return _make_response(exc, trace_id)


async def rate_limit_handler(request: Request, exc: AmapRateLimitError) -> JSONResponse:
    """高德 API 日配额 / QPS 超限 —— 额外触发 Redis 计数 + 降级提示。"""
    trace_id = str(uuid.uuid4())[:12]
    logger.error(
        "amap_rate_limit",
        code=exc.code,
        message=exc.message,
        path=request.url.path,
        trace_id=trace_id,
        quota_used=exc.details.get("quota_used"),
        quota_limit=exc.details.get("quota_limit"),
    )
    return _make_response(exc, trace_id)


async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """参数校验失败 —— 保留字段级错误信息。"""
    trace_id = str(uuid.uuid4())[:12]
    logger.warning(
        "validation_error",
        message=exc.message,
        path=request.url.path,
        trace_id=trace_id,
        details=exc.details,
    )
    return _make_response(exc, trace_id)


async def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """认证失败 —— 不暴露 details 中的敏感信息。"""
    trace_id = str(uuid.uuid4())[:12]
    logger.warning(
        "authentication_error",
        message=exc.message,
        path=request.url.path,
        trace_id=trace_id,
    )
    return _make_response(exc, trace_id, include_details=False)


async def permission_denied_handler(request: Request, exc: PermissionDeniedError) -> JSONResponse:
    trace_id = str(uuid.uuid4())[:12]
    logger.warning(
        "permission_denied",
        message=exc.message,
        path=request.url.path,
        trace_id=trace_id,
    )
    return _make_response(exc, trace_id, include_details=False)


async def not_found_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    trace_id = str(uuid.uuid4())[:12]
    logger.debug(
        "resource_not_found",
        message=exc.message,
        path=request.url.path,
        trace_id=trace_id,
    )
    return _make_response(exc, trace_id, include_details=False)


async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpenError) -> JSONResponse:
    """熔断器开启 —— 返回 503 并标记 degraded。"""
    trace_id = str(uuid.uuid4())[:12]
    logger.warning(
        "circuit_breaker_open",
        tool_name=exc.details.get("tool_name"),
        path=request.url.path,
        trace_id=trace_id,
    )
    body = _make_response(exc, trace_id)
    return body


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未知异常兜底 —— 隐藏内部细节，仅暴露 Internal Server Error。"""
    trace_id = str(uuid.uuid4())[:12]
    logger.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        trace_id=trace_id,
        traceback=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": -500,
            "message": "Internal Server Error",
            "data": None,
            "error": {
                "error_code": "INTERNAL_ERROR",
                "trace_id": trace_id,
            },
        },
    )
