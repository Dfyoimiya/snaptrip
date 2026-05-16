"""Mock API 网关 —— httpx HTTP Client 封装。

执行层与 Mock 服务（端口 8001）之间的唯一 HTTP 出口。

职责:
  - 连接池管理: httpx.AsyncClient (max_connections=20)
  - Tool 路由映射: TOOL_ROUTES 将 tool_name 映射到 HTTP 方法+路径
  - 请求注入: X-Force-Fail / X-Simulate-Delay Header 用于演示异常
  - 响应校验: HTTPError 捕获并包装为统一错误格式

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from typing import Any

import httpx


class MockAPIGateway:
    """执行层与 Mock 服务之间的 HTTP 出口"""

    TOOL_ROUTES: dict[str, tuple[str, str]] = {
        "search_poi": ("GET", "/mock/poi/search"),
        "check_queue": ("GET", "/mock/queue/{poi_id}"),
        "check_availability": ("GET", "/mock/poi/{poi_id}/availability"),
        "book_table": ("POST", "/mock/booking/table"),
        "book_ticket": ("POST", "/mock/booking/ticket"),
        "order": ("POST", "/mock/order"),
        "notify": ("POST", "/mock/notify/share"),
    }

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client: httpx.AsyncClient | None = None

    async def start(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_connections=20),
        )

    async def stop(self):
        if self.client:
            await self.client.aclose()

    async def call(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.client:
            await self.start()
        route = self.TOOL_ROUTES.get(tool_name)
        if not route:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        method, path = route
        path = path.format(**params) if "{" in path else path

        headers = {}
        if params.pop("_force_fail", False):
            headers["X-Force-Fail"] = "true"

        try:
            if not self.client:
                await self.start()
            assert self.client is not None
            resp = await self.client.request(method=method, url=path, json=params, headers=headers)
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result
        except httpx.HTTPError as e:
            return {"success": False, "error": str(e)}
