"""LLM Gateway 单元测试。

Author: SnapTrip Team
Date: 2026-05-17 / Updated 2026-05-18
"""

from __future__ import annotations

import pytest

from app.services.llm_gateway import LLMError, LLMGateway


class TestGatewayInit:
    def test_default_base_url(self, monkeypatch):
        from app.core import config
        monkeypatch.setattr(config.settings, "OPENROUTER_API_KEY", "")
        monkeypatch.setattr(config.settings, "DEEPSEEK_API_KEY", "")
        gw = LLMGateway(api_key="sk-test")
        assert gw._base_url == "https://api.deepseek.com/v1"

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
