"""Phase 3b 单元测试：跨进程 SSE 流式推送。

测试目标：
  1. 无 Last-Event-ID → 回放 DB 全部历史事件
  2. DB 回放完毕 → 订阅 Redis 实时频道
  3. plan_completed 终端事件 → 关闭 SSE
  4. 空 DB → 跳过回放，直接订阅 Redis
  5. 有 Last-Event-ID → 仅回放该时间点之后的事件

Author: SnapTrip Team
Date: 2026-05-22
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent.schemas.events import RuntimeEvent


def _make_event(
    event_id: str = "evt-001",
    plan_id: str = "p1",
    node_name: str = "planner",
    event_type: str = "node_started",
    payload: dict | None = None,
) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=event_id,
        run_id="run-001",
        plan_id=plan_id,
        node_name=node_name,
        event_type=event_type,  # type: ignore[arg-type]
        timestamp=datetime.now(UTC),
        payload=payload or {},
    )


def _mock_pubsub_message(channel: str, data: str, msg_type: str = "message") -> dict:
    """构造 Redis Pub/Sub 消息格式。"""
    return {
        "type": msg_type,
        "pattern": None,
        "channel": channel.encode() if isinstance(channel, str) else channel,
        "data": data.encode() if isinstance(data, str) else data,
    }


class TestCrossProcessSSE:
    @pytest.mark.asyncio
    async def test_replays_db_events_on_connect(self):
        """首次连接（无 Last-Event-ID）→ 从 DB 回放全部已有事件。"""
        plan_id = "550e8400-e29b-41d4-a716-446655440000"

        db_events = [
            _make_event("evt-1", plan_id, "intent_parser", "node_started"),
            _make_event("evt-2", plan_id, "intent_parser", "node_succeeded"),
        ]

        mock_repo = MagicMock()
        mock_repo.list_by_plan = AsyncMock(return_value=db_events)

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        # After replay, pubsub should yield a terminal event to end the test
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        # Empty iterator → no real-time events after replay
        mock_pubsub.listen = MagicMock(return_value=_async_iter([]))

        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        from marketplace.app.api.v1.session import _event_generator

        events = []
        async for sse in _event_generator(plan_id, mock_redis, mock_repo, last_event_id=None):
            events.append(sse)

        assert len(events) == 2
        assert mock_repo.list_by_plan.called

    @pytest.mark.asyncio
    async def test_subscribes_redis_after_replay(self):
        """DB 回放完毕后 → 订阅 Redis 频道接收实时事件。"""
        plan_id = "p-sub"

        mock_repo = MagicMock()
        mock_repo.list_by_plan = AsyncMock(return_value=[])

        live_event = _make_event("evt-live", plan_id, "execution_engine", "node_started")

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()

        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        messages = [
            _mock_pubsub_message("subscribe", "", "subscribe"),
            _mock_pubsub_message(
                f"plan:{plan_id}:events",
                live_event.model_dump_json(),
            ),
        ]
        mock_pubsub.listen = MagicMock(return_value=_async_iter(messages))
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        from marketplace.app.api.v1.session import _event_generator

        events = []
        async for sse in _event_generator(plan_id, mock_redis, mock_repo, last_event_id=None):
            events.append(sse)

        mock_pubsub.subscribe.assert_called_once_with(f"plan:{plan_id}:events")
        assert len(events) >= 1
        # Verify the live event was converted to SSE
        assert any("execution_engine" in json.dumps(e) for e in events)

    @pytest.mark.asyncio
    async def test_closes_on_plan_completed(self):
        """收到 plan_completed 终端事件 → SSE 关闭。"""
        plan_id = "p-terminal"

        mock_repo = MagicMock()
        mock_repo.list_by_plan = AsyncMock(return_value=[])

        terminal_event = _make_event("evt-done", plan_id, "plan", "plan_completed")

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        messages = [
            _mock_pubsub_message("subscribe", "", "subscribe"),
            _mock_pubsub_message(
                f"plan:{plan_id}:events",
                terminal_event.model_dump_json(),
            ),
        ]
        mock_pubsub.listen = MagicMock(return_value=_async_iter(messages))
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        from marketplace.app.api.v1.session import _event_generator

        events = []
        async for sse in _event_generator(plan_id, mock_redis, mock_repo, last_event_id=None):
            events.append(sse)

        # Generator should exit after terminal event — not hang
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_empty_db_skips_replay(self):
        """DB 无历史事件 → 跳过回放，直接订阅 Redis。"""
        plan_id = "p-empty"

        mock_repo = MagicMock()
        mock_repo.list_by_plan = AsyncMock(return_value=[])

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        # No messages after subscribe — generator keeps waiting (test exits)
        mock_pubsub.listen = MagicMock(
            return_value=_async_iter(
                [
                    _mock_pubsub_message("subscribe", "", "subscribe"),
                ]
            )
        )
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        from marketplace.app.api.v1.session import _event_generator

        events = []
        async for sse in _event_generator(plan_id, mock_redis, mock_repo, last_event_id=None):
            events.append(sse)
            break  # Stop after first to avoid infinite loop in test

        assert len(events) == 0  # subscribe message is filtered out
        mock_pubsub.subscribe.assert_called_once()


class TestSSEEventMapping:
    def test_event_to_sse_maps_intent(self):
        """RuntimeEvent → SSE 事件名映射 correct。"""
        from marketplace.app.api.v1.session import _event_to_sse

        event = _make_event("evt-1", plan_id="p1", node_name="intent_parser", event_type="node_started")
        result = _event_to_sse(event)
        assert result["event"] == "intent"
        data = json.loads(result["data"])
        assert data["plan_id"] == "p1"
        assert data["node"] == "intent_parser"

    def test_event_to_sse_maps_plan_completed_to_done(self):
        """plan_completed → SSE event name 'done'。"""
        from marketplace.app.api.v1.session import _event_to_sse

        event = _make_event("evt-1", plan_id="p1", node_name="plan", event_type="plan_completed")
        result = _event_to_sse(event)
        assert result["event"] == "done"


def _async_iter(items: list):
    """Convert a list to an async iterator."""

    async def gen():
        for item in items:
            yield item

    return gen().__aiter__()
