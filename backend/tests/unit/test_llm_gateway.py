"""LLM Gateway 单元测试。

Author: SnapTrip Team
Date: 2026-05-17 / Updated 2026-05-18
"""

from __future__ import annotations

from app.services.llm_gateway import LLMError, LLMGateway


class TestGatewayInit:
    def test_default_base_url(self):
        gw = LLMGateway(api_key="test")
        assert "api.deepseek.com" in gw._base_url

    def test_custom_api_key(self):
        gw = LLMGateway(api_key="sk-custom")
        assert gw._api_key == "sk-custom"


class TestLLMError:
    def test_with_status_code(self):
        e = LLMError("api error", status_code=429)
        assert e.status_code == 429
        assert "api error" in str(e)

    def test_without_status_code(self):
        e = LLMError("timeout")
        assert e.status_code is None
