"""Mock API 网关 — httpx HTTP Client 封装"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class MockAPIGateway:
    """执行层与 Mock 服务之间的 HTTP 出口"""

    TOOL_ROUTES: Dict[str, tuple[str, str]] = {
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
        self.client: Optional[httpx.AsyncClient] = None

    async def start(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_connections=20),
        )

    async def stop(self):
        if self.client:
            await self.client.aclose()

    async def call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
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
            resp = await self.client.request(method=method, url=path, json=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            return {"success": False, "error": str(e)}
