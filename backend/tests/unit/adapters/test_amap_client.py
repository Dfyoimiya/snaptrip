"""AmapApiClient 单元测试 —— HTTP Client 签名 / 超时 / 异常处理。

测试覆盖:
  - 签名正确性: params 自动附 key
  - 超时处理: httpx.TimeoutException → AdapterTimeoutError
  - 错误码映射: infocode → 对应异常
  - 成功响应: infocode=10000 → 正常返回
  - 429 限流: HTTP 429 → AmapRateLimitError

使用 respx 隔离 HTTP, 无需真实高德 API Key。
"""

import httpx
import pytest
from snaptrip_shared.core.exceptions import AdapterTimeoutError, AmapApiError, AmapAuthError, AmapRateLimitError

from marketplace.app.adapters.amap.client import AmapApiClient


class TestAmapApiClientSigning:
    """测试 API Key 自动签名"""

    @pytest.mark.anyio
    async def test_get_appends_api_key(self, respx_mock):
        client = AmapApiClient(api_key="test-key-123", base_url="https://restapi.amap.com")

        route = respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
            json={"status": "1", "infocode": "10000", "info": "OK", "count": "0", "pois": []}
        )

        await client.get("/v3/place/text", params={"keywords": "咖啡"})

        assert route.called
        last_request = route.calls.last.request
        assert "test-key-123" in str(last_request.url)

    @pytest.mark.anyio
    async def test_params_and_key_merged(self, respx_mock):
        from urllib.parse import unquote

        client = AmapApiClient(api_key="abc", base_url="https://restapi.amap.com")
        route = respx_mock.get("https://restapi.amap.com/v3/geocode/geo").respond(
            json={"status": "1", "infocode": "10000", "info": "OK", "count": "0", "geocodes": []}
        )

        await client.get("/v3/geocode/geo", params={"address": "故宫", "city": "北京"})

        assert route.called
        url = unquote(str(route.calls.last.request.url))
        assert "key=abc" in url
        assert "address=故宫" in url
        assert "city=北京" in url


class TestAmapApiClientErrors:
    """测试异常处理"""

    @pytest.mark.anyio
    async def test_timeout_raises_adapter_timeout(self, respx_mock):
        client = AmapApiClient(api_key="key", base_url="https://restapi.amap.com", timeout=1)
        respx_mock.get("https://restapi.amap.com/v3/place/text").mock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(AdapterTimeoutError) as exc:
            await client.get("/v3/place/text", params={})
        assert "超时" in exc.value.message

    @pytest.mark.anyio
    async def test_invalid_key_raises_auth_error(self, respx_mock):
        client = AmapApiClient(api_key="bad-key", base_url="https://restapi.amap.com")
        respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
            json={"status": "0", "infocode": "10001", "info": "KEY 无效"}
        )

        with pytest.raises(AmapAuthError):
            await client.get("/v3/place/text", params={})

    @pytest.mark.anyio
    async def test_qps_limit_raises_rate_limit(self, respx_mock):
        client = AmapApiClient(api_key="key", base_url="https://restapi.amap.com")
        respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
            json={"status": "0", "infocode": "10003", "info": "QPS 超限"}
        )

        with pytest.raises(AmapRateLimitError):
            await client.get("/v3/place/text", params={})

    @pytest.mark.anyio
    async def test_daily_quota_exhausted(self, respx_mock):
        client = AmapApiClient(api_key="key", base_url="https://restapi.amap.com")
        respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
            json={"status": "0", "infocode": "10004", "info": "日配额超限"}
        )

        with pytest.raises(AmapRateLimitError):
            await client.get("/v3/place/text", params={})

    @pytest.mark.anyio
    async def test_http_429_rate_limit(self, respx_mock):
        client = AmapApiClient(api_key="key", base_url="https://restapi.amap.com")
        respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
            status_code=429, json={"errcode": 10003, "errdetail": "QPS over limit"}
        )

        with pytest.raises(AmapRateLimitError):
            await client.get("/v3/place/text", params={})

    @pytest.mark.anyio
    async def test_unknown_infocode_raises_amap_api_error(self, respx_mock):
        client = AmapApiClient(api_key="key", base_url="https://restapi.amap.com")
        respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
            json={"status": "0", "infocode": "20000", "info": "未知错误"}
        )

        with pytest.raises(AmapApiError) as exc:
            await client.get("/v3/place/text", params={})
        assert "20000" in exc.value.details.get("infocode", "")


class TestAmapApiClientSuccess:
    """测试正常响应"""

    @pytest.mark.anyio
    async def test_success_returns_body(self, respx_mock):
        client = AmapApiClient(api_key="key", base_url="https://restapi.amap.com")
        expected = {
            "status": "1",
            "infocode": "10000",
            "info": "OK",
            "count": "1",
            "pois": [{"id": "B000A7", "name": "故宫"}],
        }
        respx_mock.get("https://restapi.amap.com/v3/place/text").respond(json=expected)

        result = await client.get("/v3/place/text", params={})
        assert result == expected
        assert result["infocode"] == "10000"
        assert len(result["pois"]) == 1

    @pytest.mark.anyio
    async def test_get_amap_client_singleton(self):
        import marketplace.app.adapters.amap.client as mod
        from marketplace.app.adapters.amap.client import get_amap_client

        mod._amap_client = None
        client1 = get_amap_client()
        client2 = get_amap_client()
        assert client1 is client2


@pytest.mark.anyio
async def test_invalid_json_response(respx_mock):
    """测试 JSON 解析失败的响应"""
    client = AmapApiClient(api_key="key", base_url="https://restapi.amap.com")
    respx_mock.get("https://restapi.amap.com/v3/place/text").respond(
        text="这不是 JSON",
        headers={"Content-Type": "text/html"},
    )

    with pytest.raises(AmapApiError) as exc:
        await client.get("/v3/place/text", params={})
    assert "PARSE_ERROR" in exc.value.details.get("infocode", "")
