"""Phase 3b 单元测试：RedisEventBus 跨进程事件总线。

测试目标：
  1. emit() → Redis PUBLISH 正确 channel + payload
  2. emit() → SQL repository.append 持久化
  3. channel 命名格式 plan:{plan_id}:events
  4. Redis 异常不传播（降级为纯 SQL）

Author: SnapTrip Team
Date: 2026-05-22
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.agent.events import RuntimeEvent


def _make_event(plan_id: str = "p1", event_type: str = "node_started") -> RuntimeEvent:
    return RuntimeEvent(
        event_id="evt-001",
        run_id="run-001",
        plan_id=plan_id,
        node_name="test_node",
        event_type=event_type,  # type: ignore[arg-type]
        timestamp=datetime.now(UTC),
        payload={"key": "value"},
    )


def _make_bus(mock_redis=None, mock_repo=None):
    """构造 RedisEventBus，mock _get_redis 返回预置 client。"""
    from app.adapters.events.redis_event_bus import RedisEventBus

    mock_pool = MagicMock()
    repo = mock_repo or MagicMock(append=AsyncMock())
    bus = RedisEventBus(pool=mock_pool, repository=repo)

    if mock_redis is not None:
        bus._redis = mock_redis

    return bus, mock_pool, repo, mock_redis


class TestRedisEventBusEmit:
    def test_emit_publishes_to_redis(self):
        """emit() → Redis PUBLISH 到正确 channel，payload 为 JSON。"""
        mock_redis = MagicMock(publish=AsyncMock())
        bus, _pool, _repo, _redis = _make_bus(mock_redis=mock_redis)
        event = _make_event()

        asyncio.run(bus.emit(event))

        channel = f"plan:{event.plan_id}:events"
        mock_redis.publish.assert_called_once()
        assert mock_redis.publish.call_args[0][0] == channel

    def test_emit_persists_to_repo(self):
        """emit() → repository.append 持久化事件。"""
        mock_redis = MagicMock(publish=AsyncMock())
        mock_repo = MagicMock(append=AsyncMock())
        bus, _pool, repo, _redis = _make_bus(mock_redis=mock_redis, mock_repo=mock_repo)
        event = _make_event()

        asyncio.run(bus.emit(event))

        repo.append.assert_called_once_with(event)

    def test_emit_swallows_redis_error(self):
        """Redis PUBLISH 失败不阻塞图执行，仅记录 warning。"""
        mock_redis = MagicMock(publish=AsyncMock(side_effect=ConnectionError("redis down")))
        mock_repo = MagicMock(append=AsyncMock())
        bus, _pool, repo, _redis = _make_bus(mock_redis=mock_redis, mock_repo=mock_repo)
        event = _make_event()

        # Should not raise — Redis failure is non-fatal for Agent execution
        asyncio.run(bus.emit(event))
        # Repo still called (persistence before publish)
        repo.append.assert_called_once()

    def test_lazy_client_creation(self):
        """首次 emit() 时 lazy 创建 Redis client。"""
        mock_redis = MagicMock(publish=AsyncMock())
        mock_repo = MagicMock(append=AsyncMock())

        from app.adapters.events.redis_event_bus import RedisEventBus

        mock_pool = MagicMock()
        bus = RedisEventBus(pool=mock_pool, repository=mock_repo)

        # Before emit, _redis is None
        assert bus._redis is None

        with patch("app.adapters.events.redis_event_bus.aioredis.Redis", return_value=mock_redis) as mock_redis_cls:
            asyncio.run(bus.emit(_make_event()))

        # Now _redis is set
        assert bus._redis is mock_redis
        mock_redis_cls.assert_called_once_with(connection_pool=mock_pool)


class TestRedisEventBusChannel:
    def test_channel_format(self):
        """channel 命名格式 plan:{plan_id}:events。"""
        mock_redis = MagicMock(publish=AsyncMock())
        bus, _pool, _repo, _redis = _make_bus(mock_redis=mock_redis)
        event = _make_event(plan_id="550e8400-e29b-41d4-a716-446655440000")

        asyncio.run(bus.emit(event))

        expected_channel = "plan:550e8400-e29b-41d4-a716-446655440000:events"
        mock_redis.publish.assert_called_once()
        assert mock_redis.publish.call_args[0][0] == expected_channel
