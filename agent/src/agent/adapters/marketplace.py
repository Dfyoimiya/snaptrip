"""Marketplace HTTP Client —— Agent ↔ Marketplace 数据隔离边界。

Agent 不直接 SELECT marketplace 表。所有用户画像 / 计划历史 / POI
查询通过此 Client 的 HTTP API 完成。

模式:
  - mock:  返回预置数据（CI / 演示 / Agent 单测）
  - live:  调用 Marketplace HTTP API（生产 / 联调）
  - hybrid: 读真实数据，写 Mock 安全操作（联调过渡）

用法:
    client = MarketplaceClient(mode="mock")
    profile = await client.get_profile(user_id)

Author: SnapTrip Team
Date: 2026-05-22
"""

from __future__ import annotations

import logging
from typing import Literal

MarketplaceMode = Literal["mock", "live", "hybrid"]

logger = logging.getLogger(__name__)

# ── mock 预置数据 ──

_MOCK_PROFILES: dict[str, dict] = {
    "user-1": {
        "preferences": {"child_age": 5, "diet": "无偏好", "allergens": []},
        "preference_embedding": [0.1] * 1536,
        "travel_style": "leisure",
    },
    "user-2": {
        "preferences": {"child_age": None, "diet": "素食", "allergens": ["花生"]},
        "preference_embedding": [0.2] * 1536,
        "travel_style": "fast_paced",
    },
}

_DEFAULT_PROFILE: dict = {
    "preferences": {"child_age": None, "diet": "无偏好", "allergens": []},
    "preference_embedding": [0.1] * 1536,
    "travel_style": "normal",
}

_MOCK_HISTORY: dict[str, dict] = {
    "user-1": {
        "types": ["restaurant", "cafe", "attraction", "activity"],
        "moods": ["亲子", "治愈", "拍照"],
        "dominant_scene": "family",
    },
    "user-2": {
        "types": ["cafe", "attraction", "restaurant"],
        "moods": ["安静", "文艺", "治愈"],
        "dominant_scene": "solo",
    },
}

_DEFAULT_HISTORY: dict[str, list[str] | str | None] = {
    "types": ["restaurant", "cafe", "attraction", "activity"],
    "moods": ["拍照", "治愈"],
    "dominant_scene": None,
}


class MarketplaceClient:
    """Agent 侧 Marketplace 访问客户端。

    同一接口，不同模式 —— Agent 的 ToolRouter 始终调用此 Client，
    不感知模式切换。
    """

    def __init__(
        self,
        *,
        mode: MarketplaceMode = "mock",
        base_url: str = "http://localhost:8081",
        timeout: float = 10.0,
    ) -> None:
        self.mode = mode
        self.base_url = base_url
        self._timeout = timeout

    # ── async API (Agent 节点内使用) ──

    async def get_profile(self, user_id: str) -> dict | None:
        """获取用户画像（偏好向量、家庭画像、旅行节奏）。

        Returns:
            dict with keys: preference_embedding, preferences, travel_style.
            None on error or not found.
        """
        if self.mode == "mock":
            return _MOCK_PROFILES.get(user_id, _DEFAULT_PROFILE)  # type: ignore[no-any-return]

        try:
            return await self._get_profile(user_id)
        except Exception:
            logger.warning(
                "marketplace_get_profile_failed user_id=%s", user_id, exc_info=True
            )
            return None

    async def get_user_history(self, user_id: str) -> dict | None:
        """获取用户历史计划偏好聚合。

        Returns:
            dict with keys: types, moods, dominant_scene.
            None on error or no history.
        """
        if self.mode == "mock":
            return _MOCK_HISTORY.get(user_id, _DEFAULT_HISTORY)

        try:
            return await self._get_user_history(user_id)
        except Exception:
            logger.warning(
                "marketplace_get_history_failed user_id=%s", user_id, exc_info=True
            )
            return None

    # ── HTTP 实现 (live / hybrid 模式) ──

    async def _get_profile(self, user_id: str) -> dict | None:
        """HTTP GET /internal/users/{user_id}/profile。"""
        import httpx

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self.base_url}/internal/users/{user_id}/profile")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _get_user_history(self, user_id: str) -> dict | None:
        """HTTP GET /internal/users/{user_id}/history。"""
        import httpx

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self.base_url}/internal/users/{user_id}/history")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    # ── sync API (Celery task / 非 async 上下文) ──

    def get_profile_sync(self, user_id: str) -> dict | None:
        """同步包装 —— 供 Celery task 等非 async 上下文使用。"""
        if self.mode == "mock":
            return _MOCK_PROFILES.get(user_id, _DEFAULT_PROFILE)  # type: ignore[no-any-return]
        # live mode: return None (sync fallback in async context is not supported)
        logger.warning("sync_get_profile called in live mode — returning None")
        return None

    def get_history_sync(self, user_id: str) -> dict | None:
        """同步包装 —— 供 Celery task 等非 async 上下文使用。"""
        if self.mode == "mock":
            return _MOCK_HISTORY.get(user_id, _DEFAULT_HISTORY)  # type: ignore[no-any-return]
        logger.warning("sync_get_history called in live mode — returning None")
        return None
