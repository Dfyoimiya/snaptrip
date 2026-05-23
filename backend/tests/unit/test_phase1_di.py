"""Phase 1 单元测试：消除全局变量 + DB 直接耦合。

测试目标：
  1. AgentRuntime — 依赖组装正确，不复用全局变量
  2. ContextLoader — 通过 UserProfileRepositoryPort 获取画像，不直接 import AsyncSessionLocal
  3. MemoryManager — 通过 PlanRepositoryPort 获取历史，不直接 import AsyncSessionLocal
  4. Graph — 通过 AgentRuntime 传入依赖，不使用 set_gateway / set_event_sink / set_v3_dependencies

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from snaptrip_shared.schemas.plan import EnrichedIntent, IntentSchema

from agent_worker.app.agent.engines.context_loader import ContextLoader
from agent_worker.app.agent.engines.memory_manager import MemoryManager
from agent_worker.app.agent.protocol import AgentContext, AgentResult

# ── 固定有效 UUID ──
_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
_INVALID_ID = "default"

# ── 向量常量（匹配 ContextLoader._DEFAULT_VECTOR / MemoryManager 默认值）──
_V1536 = 1536
_DEFAULT_VECTOR = [0.1] * _V1536
_CUSTOM_VECTOR = [0.5] * _V1536


# ====================================================================
# Mock Repositories
# ====================================================================


class MockUserProfileRepo:
    """模拟 UserProfileRepositoryPort"""

    def __init__(self, profile: dict | None = None) -> None:
        self._profile = profile
        self.get_profile_calls: list[str] = []

    async def get_profile(self, user_id: str) -> dict | None:
        self.get_profile_calls.append(user_id)
        return self._profile


class MockPlanRepo:
    """模拟 PlanRepositoryPort"""

    def __init__(self, history: dict[str, list[str]] | None = None) -> None:
        self._history = history
        self.get_user_history_calls: list[str] = []

    async def get_user_history(self, user_id: str) -> dict[str, list[str]] | None:
        self.get_user_history_calls.append(user_id)
        return self._history


def _make_profile(
    *,
    preference_embedding: list[float] | None = None,
    preferences: dict | None = None,
    travel_style: str = "relaxed",
) -> dict:
    return {
        "preference_embedding": preference_embedding or _DEFAULT_VECTOR,
        "preferences": preferences or {},
        "travel_style": travel_style,
    }


def _make_intent(**overrides: Any) -> IntentSchema:
    defaults: dict[str, Any] = {
        "city": "北京",
        "guest_count": 2,
        "scene_type": "friends",
        "type_prefs": ["restaurant", "cafe"],
    }
    defaults.update(overrides)
    return IntentSchema(**defaults)


# ====================================================================
# 1. AgentRuntime
# ====================================================================


class TestAgentRuntime:
    """AgentRuntime 依赖组装测试。

    验证：
      - AgentRuntime 可独立构造，不依赖任何全局变量
      - 所有端口均可选（缺省时 graph 使用兜底逻辑）
    """

    def test_create_minimal_runtime(self):
        """AgentRuntime 无参数构造——所有字段为 None。"""
        from agent_worker.app.agent.runtime import AgentRuntime

        rt = AgentRuntime()
        assert rt.gateway is None
        assert rt.event_sink is None
        assert rt.tool_adapter is None
        assert rt.cb_registry is None
        assert rt.idempotency is None
        assert rt.saga is None
        assert rt.confirmator is None
        assert rt.redis is None
        assert rt.user_profile_repo is None
        assert rt.plan_repo is None

    def test_create_full_runtime(self):
        """AgentRuntime 全量依赖注入。"""
        from agent_worker.app.agent.runtime import AgentRuntime

        mock_gateway = MagicMock()
        mock_event_sink = AsyncMock()
        mock_tool_adapter = MagicMock()
        mock_cb = MagicMock()
        mock_idem = MagicMock()
        mock_saga = MagicMock()
        mock_confirmator = MagicMock()
        mock_redis = MagicMock()
        mock_profile_repo = MockUserProfileRepo()
        mock_plan_repo = MockPlanRepo()

        rt = AgentRuntime(
            gateway=mock_gateway,
            event_sink=mock_event_sink,
            tool_adapter=mock_tool_adapter,
            cb_registry=mock_cb,
            idempotency=mock_idem,
            saga=mock_saga,
            confirmator=mock_confirmator,
            redis=mock_redis,
            user_profile_repo=mock_profile_repo,
            plan_repo=mock_plan_repo,
        )

        assert rt.gateway is mock_gateway
        assert rt.event_sink is mock_event_sink
        assert rt.user_profile_repo is mock_profile_repo
        assert rt.plan_repo is mock_plan_repo


# ====================================================================
# 2. ContextLoader —— 依赖注入 UserProfileRepositoryPort
# ====================================================================


class TestContextLoaderDI:
    """ContextLoader 依赖注入测试。

    验证：
      - 注入 UserProfileRepositoryPort 时，不 import/使用 AsyncSessionLocal
      - repo 返回 None → 使用 default profile
      - repo 返回 profile → EnrichedIntent 包含 profile 数据
      - 未注入 repo → 兜底返回 default profile（不查 DB）
    """

    @pytest.mark.asyncio
    async def test_repo_returns_profile(self):
        """注入 repo 返回完整画像 → EnrichedIntent 包含 profile_vector 和 preferences。"""
        profile_dict = _make_profile(
            preference_embedding=_CUSTOM_VECTOR,
            preferences={"historical_rejections": ["poi-1", "poi-2"]},
            travel_style="fast",
        )
        repo = MockUserProfileRepo(profile=profile_dict)
        loader = ContextLoader(user_profile_repo=repo)

        intent = _make_intent()
        ctx = AgentContext(
            user_id=_USER_ID,
            history=[_make_history_entry("intent_parser", intent=intent.model_dump())],
        )
        result = await loader.execute(ctx)

        enriched = EnrichedIntent(**result.data["enriched_intent"])
        assert enriched.profile_vector == _CUSTOM_VECTOR
        assert enriched.preferred_pace == "fast"
        assert enriched.historical_rejections == ["poi-1", "poi-2"]
        assert repo.get_profile_calls == [_USER_ID]

    @pytest.mark.asyncio
    async def test_repo_returns_none_uses_default(self):
        """repo 返回 None → 使用 default profile。"""
        repo = MockUserProfileRepo(profile=None)
        loader = ContextLoader(user_profile_repo=repo)

        ctx = AgentContext(
            user_id=_USER_ID,
            history=[_make_history_entry("intent_parser", intent=_make_intent().model_dump())],
        )
        result = await loader.execute(ctx)

        enriched = EnrichedIntent(**result.data["enriched_intent"])
        assert enriched.preferred_pace == "normal"
        assert enriched.historical_rejections == []

    @pytest.mark.asyncio
    async def test_no_repo_uses_default(self):
        """未注入 repo → 直接使用 default profile（不查 DB）。"""
        loader = ContextLoader()  # 不注入 repo

        ctx = AgentContext(
            user_id=_USER_ID,
            history=[_make_history_entry("intent_parser", intent=_make_intent().model_dump())],
        )
        result = await loader.execute(ctx)

        enriched = EnrichedIntent(**result.data["enriched_intent"])
        assert enriched.preferred_pace == "normal"

    @pytest.mark.asyncio
    async def test_repo_raises_uses_default(self):
        """repo 查询抛异常 → 兜底 default profile，不阻断链路。"""
        repo = MockUserProfileRepo(profile={})
        repo.get_profile = AsyncMock(side_effect=RuntimeError("DB down"))  # type: ignore[method-assign]

        loader = ContextLoader(user_profile_repo=repo)
        ctx = AgentContext(
            user_id=_USER_ID,
            history=[_make_history_entry("intent_parser", intent=_make_intent().model_dump())],
        )
        result = await loader.execute(ctx)

        enriched = EnrichedIntent(**result.data["enriched_intent"])
        assert enriched.preferred_pace == "normal"

    @pytest.mark.asyncio
    async def test_no_user_id_uses_default_without_repo_call(self):
        """user_id 无效（非 UUID）→ 不调 repo，直接返回 default。"""
        repo = MockUserProfileRepo(profile=_make_profile(travel_style="fast"))
        loader = ContextLoader(user_profile_repo=repo)

        ctx = AgentContext(
            user_id=_INVALID_ID,
            history=[_make_history_entry("intent_parser", intent=_make_intent().model_dump())],
        )
        result = await loader.execute(ctx)

        enriched = EnrichedIntent(**result.data["enriched_intent"])
        assert repo.get_profile_calls == []
        assert enriched.preferred_pace == "normal"


# ====================================================================
# 3. MemoryManager —— 依赖注入 PlanRepositoryPort
# ====================================================================


class TestMemoryManagerDI:
    """MemoryManager 依赖注入测试。

    验证：
      - 注入 PlanRepositoryPort 时，不 import/使用 AsyncSessionLocal
      - repo 返回历史 → 增强 type_prefs / mood_prefs / scene_type
      - repo 返回 None → 不修改 enriched
      - repo 抛异常 → 兜底原样返回（不阻断链路）
    """

    @pytest.mark.asyncio
    async def test_repo_returns_history_enhances_preferences(self):
        """repo 返回历史 → type_prefs 合并历史偏好，scene_type 更新。"""
        repo = MockPlanRepo(
            history={"types": ["activity", "attraction"], "moods": ["亲子", "拍照"], "dominant_scene": "family"}
        )
        manager = MemoryManager(plan_repo=repo)

        intent = _make_intent(type_prefs=["restaurant"], scene_type="solo")
        enriched = EnrichedIntent(intent=intent, profile_vector=_DEFAULT_VECTOR)
        ctx = AgentContext(
            user_id=_USER_ID,
            history=[_make_history_entry("context_loader", enriched_intent=enriched.model_dump())],
        )
        result = await manager.execute(ctx)

        enhanced = EnrichedIntent(**result.data["enriched_intent"])
        assert "activity" in enhanced.intent.type_prefs
        assert "attraction" in enhanced.intent.type_prefs
        assert enhanced.intent.scene_type == "family"
        assert repo.get_user_history_calls == [_USER_ID]

    @pytest.mark.asyncio
    async def test_repo_returns_none_preserves_original(self):
        """repo 返回 None → 不修改 enriched。"""
        repo = MockPlanRepo(history=None)
        manager = MemoryManager(plan_repo=repo)

        intent = _make_intent(scene_type="solo", type_prefs=["cafe"])
        enriched = EnrichedIntent(intent=intent, profile_vector=_DEFAULT_VECTOR)
        ctx = AgentContext(
            user_id=_USER_ID,
            history=[_make_history_entry("context_loader", enriched_intent=enriched.model_dump())],
        )
        result = await manager.execute(ctx)

        enhanced = EnrichedIntent(**result.data["enriched_intent"])
        assert enhanced.intent.scene_type == "solo"  # 未变更
        assert enhanced.intent.type_prefs == ["cafe"]  # 未合并

    @pytest.mark.asyncio
    async def test_repo_raises_preserves_original(self):
        """repo 抛异常 → 不阻断链路，原样返回 enriched。"""
        repo = MockPlanRepo(history={})
        repo.get_user_history = AsyncMock(side_effect=RuntimeError("DB down"))  # type: ignore[method-assign]

        manager = MemoryManager(plan_repo=repo)
        intent = _make_intent(scene_type="solo")
        enriched = EnrichedIntent(intent=intent, profile_vector=_DEFAULT_VECTOR)
        ctx = AgentContext(
            user_id=_USER_ID,
            history=[_make_history_entry("context_loader", enriched_intent=enriched.model_dump())],
        )
        result = await manager.execute(ctx)

        enhanced = EnrichedIntent(**result.data["enriched_intent"])
        assert enhanced.intent.scene_type == "solo"  # 异常后原样
        assert result.status != "failed"

    @pytest.mark.asyncio
    async def test_no_repo_no_user_id_skips_db(self):
        """无 repo 或 user_id 无效 → 跳过历史查询，原样返回。"""
        manager = MemoryManager()  # 无 repo

        intent = _make_intent()
        enriched = EnrichedIntent(intent=intent, profile_vector=[])
        ctx = AgentContext(
            user_id=_INVALID_ID,  # 非 UUID
            history=[_make_history_entry("context_loader", enriched_intent=enriched.model_dump())],
        )
        result = await manager.execute(ctx)

        enhanced = EnrichedIntent(**result.data["enriched_intent"])
        assert enhanced.profile_vector == _DEFAULT_VECTOR  # 补默认向量
        assert enhanced.intent.scene_type == "friends"  # 未变更


# ====================================================================
# 4. Graph 不再依赖全局变量
# ====================================================================


class TestGraphNoGlobals:
    """验证 graph.py 可以通过 AgentRuntime 传依赖，而非读取全局变量。

    注意：此测试不执行完整图（避免依赖 LangGraph compiled graph），
    只验证 build 函数接受 AgentRuntime 参数且不崩溃。
    """

    def test_build_plan_graph_with_runtime(self):
        """build_plan_graph(runtime=...) 接受 AgentRuntime 且不抛异常。"""
        from agent_worker.app.agent.graph import build_plan_graph
        from agent_worker.app.agent.runtime import AgentRuntime

        rt = AgentRuntime()
        graph = build_plan_graph(runtime=rt)
        assert graph is not None

    def test_build_single_agent_graph_with_runtime(self):
        """build_single_agent_graph(runtime=...) 接受 AgentRuntime 且不抛异常。"""
        from agent_worker.app.agent.graph import build_single_agent_graph
        from agent_worker.app.agent.runtime import AgentRuntime

        rt = AgentRuntime()
        graph = build_single_agent_graph(runtime=rt)
        assert graph is not None

    def test_build_plan_graph_without_runtime_still_works(self):
        """向后兼容：build_plan_graph() 无参数仍可调用（使用全局变量兜底）。"""
        from agent_worker.app.agent.graph import build_plan_graph

        graph = build_plan_graph()
        assert graph is not None

    def test_set_gateway_and_set_event_sink_still_exist(self):
        """向后兼容：set_gateway / set_event_sink 函数仍然可调用（deprecation path）。"""
        from agent_worker.app.agent.graph import set_event_sink, set_gateway

        # 不抛异常即可
        set_gateway(None)
        set_event_sink(None)

    def test_set_v3_dependencies_still_exist(self):
        """向后兼容：set_v3_dependencies 函数仍然可调用（deprecation path）。"""
        from agent_worker.app.agent.graph import set_v3_dependencies

        set_v3_dependencies(
            tool_adapter=None,
            cb_registry=None,
            idempotency=None,
            saga=None,
            confirmator=None,
            redis=None,
        )


# ====================================================================
# Helpers
# ====================================================================


def _make_history_entry(agent_name: str, **data: Any) -> Any:
    """构造 AgentResult 用于 AgentContext.history。"""

    return AgentResult(agent_name=agent_name, status="success", data=data)
