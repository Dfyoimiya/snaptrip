"""AdapterRegistry + AdapterRouter —— SOCID 依赖反转核心。

职责:
  - AdapterRegistry: 管理 tool_name → Adapter 实例的映射
  - AdapterRouter: 根据 tool_name 分发到正确的后端 (Amap / Mock / 缓存降级)

分发策略:
  1. 先查 AdapterRegistry 是否注册了 Amap Adapter
  2. 若 Amap 不可用 (Key 为空) → 走 Mock Gateway 降级
  3. 若 Amap 熔断 → 走缓存降级 → 最终走 Mock

工具分组:
  AMAP_TOOLS  = {search_poi, calculate_route, geocode_address, reverse_geocode, search_district}
  MOCK_TOOLS  = {get_user_profile, check_queue, check_availability, check_child_facility,
                 book_table, book_ticket, order, notify}

设计原则 (Open/Closed):
  新增高德 API 只需:
    1. 创建 Adapter 类 (继承 BaseAmapAdapter)
    2. 在 Registry 中注册: registry.register(MyAdapter())

Author: SnapTrip Team
Date: 2026-05-19
"""

from __future__ import annotations

from typing import Any

from app.adapters.adapters.district_adapter import AmapDistrictAdapter
from app.adapters.adapters.geocode_adapter import AmapGeocodeAdapter, AmapReGeocodeAdapter
from app.adapters.adapters.poi_adapter import AmapPoiAdapter
from app.adapters.adapters.route_adapter import AmapRouteAdapter
from app.adapters.base import BaseAmapAdapter
from app.core.config import settings
from app.schemas.tool import ToolInvocation, ToolResult

AMAP_TOOL_NAMES: set[str] = {
    "search_poi",
    "calculate_route",
    "geocode_address",
    "reverse_geocode",
    "search_district",
}


class AdapterRegistry:
    """工具适配器注册表 —— Open/Closed 原则实现。

    新增工具适配器通过 register() 注册, 不修改 Registry 核心代码。
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseAmapAdapter] = {}
        self._register_builtin()

    def _register_builtin(self) -> None:
        """注册内置的高德 API 适配器。"""
        self.register(AmapPoiAdapter())
        self.register(AmapRouteAdapter())
        self.register(AmapGeocodeAdapter())
        self.register(AmapReGeocodeAdapter())
        self.register(AmapDistrictAdapter())

    def register(self, adapter: BaseAmapAdapter) -> None:
        """注册一个适配器实例。

        Args:
            adapter: BaseAmapAdapter 实例
        """
        self._adapters[adapter.tool_name] = adapter

    def get(self, tool_name: str) -> BaseAmapAdapter | None:
        """获取已注册的适配器。

        Args:
            tool_name: 工具名称

        Returns:
            BaseAmapAdapter 实例或 None
        """
        return self._adapters.get(tool_name)

    def is_amap_tool(self, tool_name: str) -> bool:
        """判断工具是否支持高德 API 作为数据源。"""
        return tool_name in AMAP_TOOL_NAMES

    @property
    def registered_tools(self) -> list[str]:
        return list(self._adapters.keys())


class AdapterRouter:
    """工具调用路由器 —— 根据后端可用性分发到 Amap / Mock。

    依赖注入:
      - registry: AdapterRegistry 实例
      - mock_gateway: MockAPIGateway 实例 (可选, 降级用)

    分发逻辑:
      1. AmapTools + 有 Key → AmapAdapter.execute()
      2. AmapTools + 无 Key → degraded (使用现有 mock data)
      3. MockTools → MockGateway.call()
    """

    def __init__(
        self,
        registry: AdapterRegistry | None = None,
        mock_gateway: Any | None = None,
    ) -> None:
        self._registry = registry or AdapterRegistry()
        self._mock_gateway = mock_gateway

    def set_mock_gateway(self, gateway: Any) -> None:
        """注入 MockAPIGateway 实例 (lifespan 中调用)。"""
        self._mock_gateway = gateway

    async def dispatch(self, invocation: ToolInvocation) -> ToolResult:
        """分发工具调用到正确的后端。

        Args:
            invocation: 工具调用请求

        Returns:
            ToolResult
        """
        tool_name = invocation.tool_name
        adapter = self._registry.get(tool_name)

        if adapter and settings.AMAP_API_KEY:
            return await adapter.execute(invocation)

        if adapter and not settings.AMAP_API_KEY:
            return ToolResult(
                invocation_id=invocation.invocation_id,
                status="degraded",
                data={"source": "amap_disabled", "message": f"{tool_name}: 高德 API Key 未配置, 使用降级数据"},
                error_code="AMAP_DISABLED",
            )

        if self._mock_gateway:
            result = await self._mock_gateway.call(tool_name, invocation.params)
            return ToolResult(
                invocation_id=invocation.invocation_id,
                status=result.get("status", "success"),
                data=result.get("data"),
                error_code=result.get("error_code"),
            )

        return ToolResult(
            invocation_id=invocation.invocation_id,
            status="failure",
            error_code="UNKNOWN_TOOL",
            error_message=f"未注册的工具: {tool_name}",
        )
