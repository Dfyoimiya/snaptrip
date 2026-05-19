"""高德地图 API HTTP Client —— 统一签名、鉴权、异常包装。

职责:
  - 连接池管理: httpx.AsyncClient (单例复用)
  - 自动签名: 所有请求追加 ?key={AMAP_API_KEY}
  - 超时控制: 可配置超时 + 每请求独立 timeout
  - 异常包装: 高德 infocode ≠ 10000 → AmapApiError / AmapAuthError / AmapRateLimitError
  - 结构化日志: logger.info("amap_api_call", endpoint=..., latency_ms=...)

SOCID 原则:
  - Separation: Client 层仅负责 HTTP 通信, 不涉及业务 schema 转换
  - Dependency Inversion: 上层 Mapper/Adapter 依赖 Client 的 _request() 接口, 而非具体实现

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import (
    AdapterTimeoutError,
    AmapApiError,
    AmapAuthError,
    AmapRateLimitError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class AmapApiClient:
    """高德地图 REST API HTTP 客户端。

    使用方式:
        client = AmapApiClient()
        data = await client.get("/v3/place/text", params={"keywords": "咖啡", "city": "北京"})
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.AMAP_API_KEY
        self._base_url = (base_url or settings.AMAP_BASE_URL).rstrip("/")
        self._timeout = timeout or settings.AMAP_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """惰性初始化 httpx.AsyncClient, 确保配置已加载。"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET 请求高德 API, 自动签名。

        Args:
            path: API 路径, 如 /v3/place/text
            params: 业务参数 (不含 key)

        Returns:
            高德 API 响应 JSON body
        """
        return await self._request("GET", path, params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST 请求高德 API (较少使用, 预留)。"""
        return await self._request("POST", path, None, json)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """统一请求入口, 处理签名、超时、异常包装。

        Args:
            method: HTTP 方法
            path: API 路径
            params: URL 查询参数
            json: JSON body

        Returns:
            解析后的响应 dict

        Raises:
            AmapAuthError: Key 无效
            AmapRateLimitError: 配额 / QPS 超限
            AmapApiError: 其他高德 API 错误
            AdapterTimeoutError: 请求超时
        """
        signed_params = {"key": self._api_key}
        if params:
            signed_params.update({k: v for k, v in params.items() if v is not None})

        t0 = time.perf_counter()
        try:
            resp = await self.client.request(method=method, url=path, params=signed_params, json=json)
        except httpx.TimeoutException:
            elapsed = time.perf_counter() - t0
            logger.error("amap_timeout", path=path, elapsed_ms=int(elapsed * 1000))
            raise AdapterTimeoutError(endpoint=path, timeout_s=self._timeout)

        elapsed = time.perf_counter() - t0
        logger.info(
            "amap_api_call",
            method=method,
            path=path,
            status=resp.status_code,
            latency_ms=int(elapsed * 1000),
        )

        if resp.status_code == 429:
            raise AmapRateLimitError(details={"http_status": 429})

        try:
            body: dict[str, Any] = resp.json()
        except Exception:
            logger.error("amap_parse_error", path=path, raw=resp.text[:200])
            raise AmapApiError(infocode="PARSE_ERROR", info="响应 JSON 解析失败")

        infocode = body.get("infocode", "")
        info = body.get("info", "")

        if infocode == "10000":
            return body

        self._raise_by_infocode(infocode, info, path)

    def _raise_by_infocode(self, infocode: str, info: str, path: str) -> None:
        """根据高德 infocode 映射到业务异常。

        高德错误码参考:
          - 10001: key 错误或过期
          - 10003: QPS 超限
          - 10004: 日配额超限
          - 10005: 每日查询次数限制
          - 其他: 通用 API 错误
        """
        logger.error("amap_api_error", infocode=infocode, info=info, path=path)

        if infocode == "10001":
            raise AmapAuthError()
        elif infocode in ("10003", "10004", "10005"):
            raise AmapRateLimitError(details={"infocode": infocode, "info": info})
        else:
            raise AmapApiError(infocode=infocode, info=info)


_amap_client: AmapApiClient | None = None


def get_amap_client() -> AmapApiClient:
    """获取全局 AmapApiClient 单例 (惰性初始化)。"""
    global _amap_client
    if _amap_client is None:
        _amap_client = AmapApiClient()
    return _amap_client


async def close_amap_client() -> None:
    """关闭全局 AmapApiClient 连接。"""
    global _amap_client
    if _amap_client:
        await _amap_client.close()
        _amap_client = None
