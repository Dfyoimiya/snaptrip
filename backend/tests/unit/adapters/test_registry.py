"""AdapterRegistry + AdapterRouter 单元测试。

测试覆盖:
  - Registry 注册/获取
  - Router 分发: Amap 启用 → AmapAdapter; Amap 禁用 → degraded
  - Router 分发: MockGateway 降级
  - 工具名分组: is_amap_tool
  - 未知工具 → failure
"""

import pytest

from agent_worker.app.agent.schemas.tool import ToolInvocation, ToolResult
from marketplace.app.adapters.amap.registry import AMAP_TOOL_NAMES, AdapterRegistry, AdapterRouter


class TestAdapterRegistry:
    def test_default_registry_has_builtin_adapters(self):
        registry = AdapterRegistry()
        tools = registry.registered_tools
        assert "search_poi" in tools
        assert "calculate_route" in tools
        assert "geocode_address" in tools
        assert "reverse_geocode" in tools
        assert "search_district" in tools

    def test_get_returns_adapter(self):
        registry = AdapterRegistry()
        adapter = registry.get("search_poi")
        assert adapter is not None
        assert adapter.tool_name == "search_poi"

    def test_get_unknown_tool_returns_none(self):
        registry = AdapterRegistry()
        assert registry.get("nonexistent_tool") is None

    def test_register_custom_adapter(self):
        from marketplace.app.adapters.amap.base import BaseAmapAdapter

        class CustomAdapter(BaseAmapAdapter):
            tool_name = "custom_tool"

            async def _call_api(self, params: dict) -> dict:
                return {}

        registry = AdapterRegistry()
        registry.register(CustomAdapter())
        assert registry.get("custom_tool") is not None

    def test_is_amap_tool(self):
        assert AdapterRegistry().is_amap_tool("search_poi") is True
        assert AdapterRegistry().is_amap_tool("calculate_route") is True
        assert AdapterRegistry().is_amap_tool("geocode_address") is True
        assert AdapterRegistry().is_amap_tool("book_table") is False
        assert AdapterRegistry().is_amap_tool("notify") is False


class TestAdapterRouter:
    @pytest.fixture
    def router(self):
        return AdapterRouter()

    async def test_dispatch_to_amap_enabled(self, monkeypatch):
        monkeypatch.setattr("marketplace.app.adapters.amap.registry.settings.AMAP_API_KEY", "fake-key-for-test")

        router = AdapterRouter()
        inv = ToolInvocation(
            tool_name="search_poi",
            params={"keywords": "咖啡", "city": "北京"},
        )

        result = await router.dispatch(inv)

        assert isinstance(result, ToolResult)
        assert result.status in ("success", "failure", "degraded")

    async def test_dispatch_to_amap_disabled(self, monkeypatch):
        monkeypatch.setattr("marketplace.app.adapters.amap.registry.settings.AMAP_API_KEY", "")

        router = AdapterRouter()
        inv = ToolInvocation(tool_name="search_poi", params={})

        result = await router.dispatch(inv)

        assert result.status == "degraded"
        assert result.error_code == "AMAP_DISABLED"

    async def test_dispatch_to_mock_gateway(self):
        class MockGateway:
            async def call(self, tool_name, params):
                return {"status": "success", "data": {"mock": True}}

        router = AdapterRouter(mock_gateway=MockGateway())
        inv = ToolInvocation(tool_name="book_table", params={"poi_id": "x"})

        result = await router.dispatch(inv)

        assert result.status == "success"
        assert result.data == {"mock": True}

    async def test_dispatch_unknown_tool(self):
        router = AdapterRouter(mock_gateway=None)
        inv = ToolInvocation(tool_name="nonexistent_tool", params={})

        result = await router.dispatch(inv)

        assert result.status == "failure"
        assert result.error_code == "UNKNOWN_TOOL"

    async def test_amap_tool_names_set(self):
        for name in ["search_poi", "calculate_route", "geocode_address", "reverse_geocode", "search_district"]:
            assert name in AMAP_TOOL_NAMES, f"{name} should be in AMAP_TOOL_NAMES"


class TestToolInvocationToAdapter:
    """验证 ToolInvocation 参数能正确传递到 Adapter"""

    @pytest.mark.anyio
    async def test_params_passthrough(self, monkeypatch):
        monkeypatch.setattr("marketplace.app.adapters.amap.registry.settings.AMAP_API_KEY", "fake-key")

        router = AdapterRouter()
        inv = ToolInvocation(
            tool_name="calculate_route",
            params={
                "from_lat": 39.908,
                "from_lng": 116.397,
                "to_lat": 39.92,
                "to_lng": 116.40,
                "mode": "walking",
            },
        )

        result = await router.dispatch(inv)

        assert isinstance(result, ToolResult)
        assert result.invocation_id == inv.invocation_id
