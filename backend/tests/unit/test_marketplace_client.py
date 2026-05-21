"""Phase 4 单元测试：Marketplace HTTP Client 隔离层。

测试目标：
  1. mock 模式返回预置数据
  2. get_profile → 返回画像或 None
  3. get_user_history → 返回历史偏好或 None
  4. 网络错误不传播（降级为 None）

Author: SnapTrip Team
Date: 2026-05-22
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestMarketplaceClientMock:
    def test_mock_mode_get_profile_returns_data(self):
        """mock 模式 get_profile → 返回预置画像数据。"""
        from agent_worker.app.agent.adapters.marketplace import MarketplaceClient

        client = MarketplaceClient(mode="mock")
        result = client.get_profile_sync("user-1")
        assert result is not None
        assert "preferences" in result

    def test_mock_mode_get_profile_unknown_user(self):
        """mock 模式未知用户 → 返回默认画像。"""
        from agent_worker.app.agent.adapters.marketplace import MarketplaceClient

        client = MarketplaceClient(mode="mock")
        result = client.get_profile_sync("unknown-user")
        # Mock mode returns default profile for all users
        assert result is not None

    def test_mock_mode_get_history_returns_data(self):
        """mock 模式 get_user_history → 返回预置偏好聚合。"""
        from agent_worker.app.agent.adapters.marketplace import MarketplaceClient

        client = MarketplaceClient(mode="mock")
        result = client.get_history_sync("user-1")
        assert result is not None
        assert "dominant_scene" in result
        assert "types" in result


class TestMarketplaceClientHTTP:
    @pytest.mark.asyncio
    async def test_live_mode_get_profile_calls_api(self):
        """live 模式 get_profile → 调用 HTTP API。"""
        from agent_worker.app.agent.adapters.marketplace import MarketplaceClient

        client = MarketplaceClient(mode="live", base_url="http://marketplace:8081")

        with patch.object(client, "_get_profile", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"preferences": {"diet": "vegan"}}
            result = await client.get_profile("user-1")
            assert result == {"preferences": {"diet": "vegan"}}
            mock_get.assert_called_once_with("user-1")

    @pytest.mark.asyncio
    async def test_live_mode_handles_network_error(self):
        """live 模式网络错误 → 返回 None，不抛异常。"""
        from agent_worker.app.agent.adapters.marketplace import MarketplaceClient

        client = MarketplaceClient(mode="live", base_url="http://marketplace:8081")

        with patch.object(client, "_get_profile", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ConnectionError("refused")
            result = await client.get_profile("user-1")
            assert result is None


class TestMarketplaceClientModeSwitch:
    def test_default_mode_is_mock(self):
        """默认模式为 mock。"""
        from agent_worker.app.agent.adapters.marketplace import MarketplaceClient

        client = MarketplaceClient()
        assert client.mode == "mock"

    def test_live_mode_uses_configured_url(self):
        """live 模式使用配置的 base_url。"""
        from agent_worker.app.agent.adapters.marketplace import MarketplaceClient

        client = MarketplaceClient(mode="live", base_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"
