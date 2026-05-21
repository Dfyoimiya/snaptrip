"""集成测试 —— 高德真实 API 测试 (需要有效 AMAP_API_KEY)。

运行方式:
  pytest tests/integration/ -m "amap" -v    # 需要有效 Key
  pytest tests/integration/ -m "ci" -v       # CI 环境 (Mock 降级路径)

测试分组:
  - amap 标记: 真实高德 API 调用 (消耗配额, 可选跑)
  - ci   标记: CI 环境可执行 (不需要 Key)

Author: SnapTrip Team
Date: 2026-05-19
"""


import pytest

from shared.core.config import settings

AMAP_INTEGRATION = len(settings.AMAP_API_KEY) >= 8
_amap_skip = pytest.mark.skipif(not AMAP_INTEGRATION, reason="需要 AMAP_API_KEY")

pytestmark_ci = pytest.mark.ci


# ===== CI 降级链路测试 (不需要真实 Key) =====


@pytest.mark.anyio
class TestDegradationPath:
    """降级链路: 无 Key → degraded → mock data"""

    async def test_search_poi_degraded_when_key_missing(self, monkeypatch):
        monkeypatch.setattr("marketplace.app.adapters.amap.registry.settings.AMAP_API_KEY", "")

        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.registry import AdapterRouter

        router = AdapterRouter()
        inv = ToolInvocation(
            tool_name="search_poi",
            params={"city": "北京", "keywords": "咖啡"},
        )
        result = await router.dispatch(inv)

        assert result.status == "degraded"
        assert result.error_code == "AMAP_DISABLED"
        assert "降级" in result.data.get("message", "")

    async def test_calculate_route_degraded_when_key_missing(self, monkeypatch):
        monkeypatch.setattr("marketplace.app.adapters.amap.registry.settings.AMAP_API_KEY", "")

        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.registry import AdapterRouter

        router = AdapterRouter()
        inv = ToolInvocation(
            tool_name="calculate_route",
            params={"from_lat": 39.9, "from_lng": 116.4, "to_lat": 39.92, "to_lng": 116.41},
        )
        result = await router.dispatch(inv)

        assert result.status == "degraded"
        assert result.error_code == "AMAP_DISABLED"

    async def test_mock_tools_still_work(self):
        """Mock tools (book_table等) 不依赖高德, 即使 Key 缺失也能用 MockGateway"""
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.registry import AdapterRouter

        class MinimalMockGateway:
            async def call(self, tool_name, params):
                return {"status": "success", "data": {"booking_id": "bk-test-001"}}

        router = AdapterRouter(mock_gateway=MinimalMockGateway())
        inv = ToolInvocation(
            tool_name="book_table",
            params={"poi_id": "test", "guest_count": 2, "time_slot": "18:00-19:00"},
        )
        result = await router.dispatch(inv)

        assert result.status == "success"
        assert result.data["booking_id"] == "bk-test-001"


# ===== 真实高德 API 测试 (需要 AMAP_API_KEY) =====


@_amap_skip
@pytest.mark.anyio
class TestRealAmapAPI:
    """真实高德 API 功能测试 (消耗配额, 需 Key 和网络)"""

    async def test_search_poi_real(self):
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.poi_adapter import AmapPoiAdapter

        adapter = AmapPoiAdapter()
        inv = ToolInvocation(
            tool_name="search_poi",
            params={"city": "北京", "keywords": "故宫", "limit": 5},
        )
        result = await adapter.execute(inv)

        assert result.status == "success", f"FAILED: {result.error_code} - {result.error_message}"
        assert result.data is not None
        assert result.data["source"] == "amap"
        assert result.data["total"] > 0
        assert len(result.data["pois"]) > 0
        assert any("故宫" in p["name"] for p in result.data["pois"])

    async def test_search_poi_by_category(self):
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.poi_adapter import AmapPoiAdapter

        adapter = AmapPoiAdapter()
        inv = ToolInvocation(
            tool_name="search_poi",
            params={"city": "北京", "category": "restaurant", "limit": 5},
        )
        result = await adapter.execute(inv)

        assert result.status == "success", f"FAILED: {result.error_code} - {result.error_message}"
        assert result.data is not None
        assert result.data["source"] == "amap"
        assert len(result.data["pois"]) > 0

    async def test_geocode_real(self):
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.geocode_adapter import AmapGeocodeAdapter

        adapter = AmapGeocodeAdapter()
        inv = ToolInvocation(
            tool_name="geocode_address",
            params={"address": "北京市东城区故宫"},
        )
        result = await adapter.execute(inv)

        assert result.status == "success", f"FAILED: {result.error_code} - {result.error_message}"
        assert result.data is not None
        assert result.data["count"] >= 1
        assert result.data["results"][0]["lat"] != 0.0
        assert result.data["results"][0]["lng"] != 0.0

    async def test_reverse_geocode_real(self):
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.geocode_adapter import AmapReGeocodeAdapter

        adapter = AmapReGeocodeAdapter()
        inv = ToolInvocation(
            tool_name="reverse_geocode",
            params={"lat": 39.908, "lng": 116.397},
        )
        result = await adapter.execute(inv)

        assert result.status == "success", f"FAILED: {result.error_code} - {result.error_message}"
        assert result.data is not None
        assert len(result.data["formatted_address"]) > 0

    async def test_walking_route_real(self):
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.route_adapter import AmapRouteAdapter

        adapter = AmapRouteAdapter()
        inv = ToolInvocation(
            tool_name="calculate_route",
            params={
                "from_lat": 39.908, "from_lng": 116.397,  # 故宫
                "to_lat": 39.937, "to_lng": 116.403,  # 南锣鼓巷
                "mode": "walking",
            },
        )
        result = await adapter.execute(inv)

        assert result.status == "success", f"FAILED: {result.error_code} - {result.error_message}"
        assert result.data is not None
        assert result.data["distance_km"] > 0
        assert result.data["duration_min"] > 0

    async def test_search_district_real(self):
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.district_adapter import AmapDistrictAdapter

        adapter = AmapDistrictAdapter()
        inv = ToolInvocation(
            tool_name="search_district",
            params={"keywords": "北京", "subdistrict": 0},
        )
        result = await adapter.execute(inv)

        assert result.status == "success", f"FAILED: {result.error_code} - {result.error_message}"
        assert result.data is not None
        assert result.data["count"] >= 1
        assert result.data["results"][0]["name"] == "北京市"


# ===== 异常路径集成测试 (使用 Mock, 不需真实 Key) =====


@pytest.mark.anyio
class TestErrorHandlingIntegration:
    """异常处理集成测试 —— 验证异常正确传播与包装"""

    async def test_adapter_timeout_propagates(self, respx_mock):
        import httpx

        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.poi_adapter import AmapPoiAdapter

        respx_mock.get("https://restapi.amap.com/v3/place/text").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        adapter = AmapPoiAdapter()
        inv = ToolInvocation(
            tool_name="search_poi",
            params={"keywords": "咖啡", "city": "北京"},
        )
        result = await adapter.execute(inv)

        assert result.status == "failure"
        assert "ADAPTERTIMEOUTERROR" in result.error_code or "timeout" in result.error_message.lower()

    async def test_invalid_key_handling(self, respx_mock):
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.poi_adapter import AmapPoiAdapter

        respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
            json={"status": "0", "infocode": "10001", "info": "INVALID_USER_KEY"}
        )

        adapter = AmapPoiAdapter()
        inv = ToolInvocation(
            tool_name="search_poi",
            params={"keywords": "咖啡", "city": "北京"},
        )
        result = await adapter.execute(inv)

        assert result.status == "failure"
        assert "AMAPAUTHERROR" in result.error_code or "KEY" in result.error_message

    async def test_router_graceful_unknown_tool(self):
        from agent_worker.app.agent.schemas.tool import ToolInvocation
        from marketplace.app.adapters.amap.registry import AdapterRouter

        router = AdapterRouter()
        inv = ToolInvocation(tool_name="completely_unknown_tool", params={})

        result = await router.dispatch(inv)

        assert result.status == "failure"
        assert result.error_code == "UNKNOWN_TOOL"
