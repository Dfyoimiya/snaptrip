"""统一异常层级 —— SOCID 原则的 Consistent Exception 实现。

所有业务异常继承 SnapTripException，携带 code / message / status_code / details 四元组。
由 exception_handlers.py 的全局处理器统一转换为 {code, message, data} 响应。

层级结构:
  SnapTripException
  ├── 4xx 客户端异常
  │   ├── ValidationError (422)
  │   ├── AuthenticationError (401)
  │   ├── PermissionDeniedError (403)
  │   └── ResourceNotFoundError (404)
  ├── 5xx 服务端异常
  │   ├── AgentError (500)
  │   ├── AdapterError (502)         ← 高德 API 适配失败基类
  │   ├── GatewayError (502)
  │   └── ServiceUnavailableError (503)
  └── CircuitBreakerOpenError (503)

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from typing import Any


class SnapTripException(Exception):  # noqa: N818
    """业务异常基类。

    Attributes:
        code: 业务错误码字符串，如 "AMAP_RATE_LIMIT"
        message: 人类可读错误描述
        status_code: HTTP 状态码
        details: 附加上下文字典，用于前端展示或排查
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, status={self.status_code})"


# ===== 4xx 客户端异常 =====


class ValidationError(SnapTripException):
    """请求参数校验失败"""

    def __init__(self, message: str = "参数校验失败", details: dict | None = None) -> None:
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)


class AuthenticationError(SnapTripException):
    """认证失败 —— JWT 过期 / 无效 / 缺失"""

    def __init__(self, message: str = "认证失败，请重新登录", details: dict | None = None) -> None:
        super().__init__(code="AUTHENTICATION_ERROR", message=message, status_code=401, details=details)


class PermissionDeniedError(SnapTripException):
    """无权限访问资源"""

    def __init__(self, message: str = "无权限访问此资源", details: dict | None = None) -> None:
        super().__init__(code="PERMISSION_DENIED", message=message, status_code=403, details=details)


class ResourceNotFoundError(SnapTripException):
    """资源不存在 —— Plan / POI / User 等"""

    def __init__(self, resource: str = "资源", identifier: str = "", details: dict | None = None) -> None:
        msg = f"{resource}不存在" + (f": {identifier}" if identifier else "")
        super().__init__(code="RESOURCE_NOT_FOUND", message=msg, status_code=404, details=details)


# ===== 5xx Agent 异常 =====


class AgentError(SnapTripException):
    """Agent 执行失败基类"""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(code=code, message=message, status_code=500, details=details)


class IntentParseError(AgentError):
    """意图解析失败"""

    def __init__(self, message: str = "无法解析用户意图", details: dict | None = None) -> None:
        super().__init__(code="INTENT_PARSE_ERROR", message=message, details=details)


class PlanningError(AgentError):
    """规划引擎失败"""

    def __init__(self, message: str = "计划生成失败", details: dict | None = None) -> None:
        super().__init__(code="PLANNING_ERROR", message=message, details=details)


class ExecutionError(AgentError):
    """执行引擎失败"""

    def __init__(self, message: str = "计划执行失败", details: dict | None = None) -> None:
        super().__init__(code="EXECUTION_ERROR", message=message, details=details)


# ===== 5xx Adapter 异常 (高德 API 适配层) =====


class AdapterError(SnapTripException):
    """外部 API 适配失败基类。

    所有高德 API 相关异常的公共父类，status_code=502 (Bad Gateway)。
    """

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(code=code, message=message, status_code=502, details=details)


class AmapApiError(AdapterError):
    """高德 API 返回非成功状态 (infocode != 10000)"""

    def __init__(self, infocode: str = "", info: str = "", details: dict | None = None) -> None:
        _details = details or {}
        _details["infocode"] = infocode
        _details["info"] = info
        super().__init__(
            code="AMAP_API_ERROR",
            message=f"高德API返回错误: {info} (infocode={infocode})",
            details=_details,
        )


class AmapAuthError(AdapterError):
    """高德 API Key 无效或过期 (infocode=10001)"""

    def __init__(self, message: str = "高德API Key 无效，请检查 AMAP_API_KEY 配置") -> None:
        super().__init__(code="AMAP_AUTH_ERROR", message=message)


class AmapRateLimitError(AdapterError):
    """高德 API 日配额 / QPS 超限 (infocode=10003 或 HTTP 429)"""

    def __init__(self, quota_used: int = 0, quota_limit: int = 0, details: dict | None = None) -> None:
        _details = details or {}
        _details["quota_used"] = quota_used
        _details["quota_limit"] = quota_limit
        super().__init__(
            code="AMAP_RATE_LIMIT",
            message=f"高德API日配额已用尽 ({quota_used}/{quota_limit})" if quota_limit else "高德API QPS 超限",
            details=_details,
        )


class AdapterTimeoutError(AdapterError):
    """适配器调用超时"""

    def __init__(self, endpoint: str = "", timeout_s: float = 0, details: dict | None = None) -> None:
        _details = details or {}
        _details["endpoint"] = endpoint
        _details["timeout_s"] = timeout_s
        super().__init__(code="ADAPTER_TIMEOUT", message=f"调用 {endpoint} 超时 ({timeout_s}s)", details=_details)


# ===== 5xx Gateway 异常 =====


class GatewayError(SnapTripException):
    """网关异常基类 —— Mock / LLM 等"""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(code=code, message=message, status_code=502, details=details)


class MockApiError(GatewayError):
    """Mock 服务异常"""

    def __init__(self, message: str = "Mock 服务不可用", details: dict | None = None) -> None:
        super().__init__(code="MOCK_API_ERROR", message=message, details=details)


class LLMError(GatewayError):
    """LLM 调用异常"""

    def __init__(self, message: str = "LLM 调用失败", details: dict | None = None) -> None:
        super().__init__(code="LLM_ERROR", message=message, details=details)


# ===== 5xx 基础设施异常 =====


class ServiceUnavailableError(SnapTripException):
    """基础设施不可用 —— DB / Redis / Celery"""

    def __init__(self, service: str = "服务", details: dict | None = None) -> None:
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=f"{service}不可用，请稍后重试",
            status_code=503,
            details=details,
        )


class CircuitBreakerOpenError(SnapTripException):
    """熔断器已开启"""

    def __init__(self, tool_name: str = "", details: dict | None = None) -> None:
        _details = details or {}
        _details["tool_name"] = tool_name
        super().__init__(
            code="CIRCUIT_BREAKER_OPEN",
            message=f"熔断器 {tool_name} 已开启，已拒绝请求" if tool_name else "熔断器已开启",
            status_code=503,
            details=_details,
        )
