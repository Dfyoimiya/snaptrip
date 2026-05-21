"""BaseAmapAdapter / Adapter 单元测试 —— POI / Route / Geocode Adapter 业务逻辑。

测试覆盖:
  - BaseAmapAdapter.execute(): 参数校验 + 正常调用 + 异常捕获
  - AmapPoiAdapter: validate + _call_api (关键词搜索 / 周边搜索)
  - AmapRouteAdapter: 起终点构建
  - AmapGeocodeAdapter: 地址 → 坐标
  - AmapReGeocodeAdapter: 坐标 → 地址
  - AmapDistrictAdapter: 行政区查询

使用 respx mock 高德 HTTP 响应, 验证参数组装和数据返回格式。
"""

import pytest

from agent_worker.app.agent.schemas.tool import ToolInvocation, ToolResult
from marketplace.app.adapters.amap.base import BaseAmapAdapter
from marketplace.app.adapters.amap.district_adapter import AmapDistrictAdapter
from marketplace.app.adapters.amap.geocode_adapter import AmapGeocodeAdapter, AmapReGeocodeAdapter
from marketplace.app.adapters.amap.poi_adapter import AmapPoiAdapter
from marketplace.app.adapters.amap.route_adapter import AmapRouteAdapter


@pytest.fixture(autouse=True)
def reset_amap_client_singleton():
    """每个测试前重置 AmapApiClient 单例, 确保 respx mock 生效。"""
    import marketplace.app.adapters.amap.client as mod
    mod._amap_client = None
    yield
    mod._amap_client = None


class TestBaseAmapAdapter:
    """BaseAmapAdapter 抽象基类行为测试"""

    async def test_execute_returns_success(self):
        class TestAdapter(BaseAmapAdapter):
            tool_name = "test_tool"

            async def _call_api(self, params: dict) -> dict:
                return {"result": "ok"}

        adapter = TestAdapter()
        inv = ToolInvocation(tool_name="test_tool", params={"key": "val"})
        result = await adapter.execute(inv)

        assert isinstance(result, ToolResult)
        assert result.status == "success"
        assert result.data == {"result": "ok"}
        assert result.latency_ms >= 0

    async def test_execute_catches_exception(self):
        class FailAdapter(BaseAmapAdapter):
            tool_name = "fail_tool"

            async def _call_api(self, params: dict) -> dict:
                raise RuntimeError("模拟失败")

        adapter = FailAdapter()
        inv = ToolInvocation(tool_name="fail_tool", params={})
        result = await adapter.execute(inv)

        assert result.status == "failure"
        assert result.error_code == "RUNTIMEERROR"
        assert "模拟失败" in result.error_message

    async def test_validate_failure_returns_error(self):
        class StrictAdapter(BaseAmapAdapter):
            tool_name = "strict"

            async def validate(self, params: dict) -> bool:
                return bool(params.get("required_field"))

            async def _call_api(self, params: dict) -> dict:
                return {}

        adapter = StrictAdapter()
        inv = ToolInvocation(tool_name="strict", params={"other": "x"})
        result = await adapter.execute(inv)

        assert result.status == "failure"
        assert result.error_code == "INVALID_PARAMS"


# ===== Standalone async tests with respx_mock =====


@pytest.mark.anyio
async def test_keyword_search(respx_mock):
    respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
        json={
            "status": "1",
            "infocode": "10000",
            "info": "OK",
            "count": "2",
            "pois": [
                {"id": "B001", "name": "故宫", "typecode": "110100",
                 "location": "116.397,39.908", "cityname": "北京",
                 "biz_ext": {"rating": "4.8", "cost": "60"}},
                {"id": "B002", "name": "南锣咖啡", "typecode": "050100",
                 "location": "116.40,39.94", "cityname": "北京",
                 "biz_ext": {"rating": "4.5", "cost": "45"}},
            ],
        }
    )

    adapter = AmapPoiAdapter()
    inv = ToolInvocation(
        tool_name="search_poi",
        params={"keywords": "咖啡", "city": "北京"},
    )
    result = await adapter.execute(inv)

    assert result.status == "success", f"Status: {result.status}, error: {result.error_message}"
    assert result.data is not None
    assert result.data["source"] == "amap"
    assert result.data["total"] == 2
    assert len(result.data["pois"]) == 2


@pytest.mark.anyio
async def test_walking_route(respx_mock):
    respx_mock.get("https://restapi.amap.com/v3/direction/walking").respond(
        json={
            "status": "1",
            "infocode": "10000",
            "info": "OK",
            "route": {
                "origin": "116.397,39.908",
                "destination": "116.40,39.92",
                "paths": [{
                    "distance": "1500",
                    "duration": "900",
                    "steps": [],
                    "tolls": "0",
                    "traffic_lights": "0",
                }],
            },
        }
    )

    adapter = AmapRouteAdapter()
    inv = ToolInvocation(
        tool_name="calculate_route",
        params={
            "from_lat": 39.908, "from_lng": 116.397,
            "to_lat": 39.92, "to_lng": 116.40,
            "mode": "walking",
        },
    )
    result = await adapter.execute(inv)

    assert result.status == "success", f"Status: {result.status}, error: {result.error_message}"
    assert result.data is not None
    assert result.data["distance_km"] == 1.5
    assert result.data["duration_min"] == 15


@pytest.mark.anyio
async def test_geocode_address(respx_mock):
    respx_mock.get("https://restapi.amap.com/v3/geocode/geo").respond(
        json={
            "status": "1",
            "infocode": "10000",
            "info": "OK",
            "count": "1",
            "geocodes": [{
                "formatted_address": "北京市东城区故宫",
                "country": "中国",
                "province": "北京市",
                "city": "北京市",
                "district": "东城区",
                "location": "116.397,39.908",
                "level": "兴趣点",
            }],
        }
    )

    adapter = AmapGeocodeAdapter()
    inv = ToolInvocation(
        tool_name="geocode_address",
        params={"address": "故宫", "city": "北京"},
    )
    result = await adapter.execute(inv)

    assert result.status == "success", f"Status: {result.status}, error: {result.error_message}"
    assert result.data is not None
    assert result.data["source"] == "amap"
    assert result.data["count"] == 1
    assert result.data["results"][0]["lat"] == 39.908
    assert result.data["results"][0]["lng"] == 116.397


@pytest.mark.anyio
async def test_reverse_geocode(respx_mock):
    respx_mock.get("https://restapi.amap.com/v3/geocode/regeo").respond(
        json={
            "status": "1",
            "infocode": "10000",
            "info": "OK",
            "regeocode": {
                "formatted_address": "北京市朝阳区三里屯太古里",
                "addressComponent": {
                    "country": "中国",
                    "province": "北京市",
                    "city": "北京市",
                    "citycode": "010",
                    "district": "朝阳区",
                    "adcode": "110105",
                    "township": "三里屯街道",
                },
            },
        }
    )

    adapter = AmapReGeocodeAdapter()
    inv = ToolInvocation(
        tool_name="reverse_geocode",
        params={"lat": 39.908, "lng": 116.397},
    )
    result = await adapter.execute(inv)

    assert result.status == "success", f"Status: {result.status}, error: {result.error_message}"
    assert result.data is not None
    assert result.data["source"] == "amap"
    assert "三里屯" in result.data["formatted_address"]
    assert result.data["district"] == "朝阳区"


@pytest.mark.anyio
async def test_search_district(respx_mock):
    respx_mock.get("https://restapi.amap.com/v3/config/district").respond(
        json={
            "status": "1",
            "infocode": "10000",
            "info": "OK",
            "count": "1",
            "districts": [{"citycode": "010", "adcode": "110000", "name": "北京市",
                           "center": "116.407,39.904", "level": "city", "districts": []}],
        }
    )

    adapter = AmapDistrictAdapter()
    inv = ToolInvocation(
        tool_name="search_district",
        params={"keywords": "北京", "subdistrict": 0},
    )
    result = await adapter.execute(inv)

    assert result.status == "success", f"Status: {result.status}, error: {result.error_message}"
    assert result.data is not None
    assert result.data["source"] == "amap"
    assert result.data["count"] == 1
    assert result.data["results"][0]["name"] == "北京市"
    assert result.data["results"][0]["center_lat"] == 39.904
    assert result.data["results"][0]["center_lng"] == 116.407
