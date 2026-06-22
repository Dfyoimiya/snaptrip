"""Shared HTTP client for agent systems calling marketplace backend APIs.

Provides a unified HTTP client with:
  - Configurable base URL (env SNAPTRIP_MARKETPLACE_URL)
  - JWT passthrough via ContextVar (set by caller before request)
  - Timeout control per request type
  - Response unwrapping (success() wrapper)
  - Exponential backoff retry via tenacity

Usage:
    from shared.http_client import MarketplaceClient

    client = MarketplaceClient()
    products = await client.get("/api/v1/portal/products", params={"keyword": "手机"})
    detail = await client.get(f"/api/v1/portal/products/{product_id}")
    recs = await client.post("/api/v1/portal/recommendations", json={"scene": "homepage", "num_items": 10})

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.auth import auth_header

logger = logging.getLogger(__name__)

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")

RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    ConnectionError,
    TimeoutError,
    OSError,
)


class MarketplaceClient:
    """Shared async HTTP client for marketplace backend API calls.

    Key behaviors:
      - Injects JWT via ContextVar (set_auth_token must be called first)
      - Unwraps success() wrapper: {"code": 0, "message": "success", "data": {...}} → {...}
      - Retries on transient network errors with exponential backoff
      - Default timeout of 10s, configurable per request
    """

    def __init__(self, base_url: str = "", default_timeout: float = 10.0):
        self.base_url = base_url or MARKETPLACE_URL
        self.default_timeout = default_timeout

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry, unwrap response, and return data."""
        url = f"{self.base_url}{path}"
        timeout_val = timeout or self.default_timeout
        headers = {**auth_header(), "Content-Type": "application/json"}

        async def _do():
            async with httpx.AsyncClient(timeout=timeout_val) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return data

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            reraise=True,
        ):
            with attempt:
                return await _do()

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """GET request → unwrap response data dict."""
        raw = await self._request("GET", path, params=params, timeout=timeout)
        return self._unwrap(raw)

    async def post(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """POST request → unwrap response data dict."""
        raw = await self._request("POST", path, json_data=json_data, timeout=timeout)
        return self._unwrap(raw)

    @staticmethod
    def _unwrap(raw: dict[str, Any]) -> dict[str, Any]:
        """Unwrap the success() wrapper from backend API responses.

        Backend returns: {"code": 0, "message": "success", "data": {...}}
        This returns the inner data dict.
        """
        if isinstance(raw, dict) and "data" in raw and "code" in raw:
            return raw["data"]
        return raw
