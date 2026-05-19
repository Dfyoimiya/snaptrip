"""MemoryService + Celery 单元测试。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import os
import uuid

import pytest

from app.services.memory_service import MemoryService

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
async def memory():
    svc = MemoryService(redis_url=REDIS_URL)
    await svc.start()
    yield svc
    await svc.stop()


@pytest.mark.asyncio
async def test_set_and_get_session_state(memory: MemoryService):
    sid = _uid()
    await memory.set_session_state(sid, "planning", ttl=60)
    state = await memory.get_session_state(sid)
    assert state == "planning"


@pytest.mark.asyncio
async def test_get_session_state_missing(memory: MemoryService):
    state = await memory.get_session_state("nonexistent-" + _uid())
    assert state is None


@pytest.mark.asyncio
async def test_push_and_get_dialogue(memory: MemoryService):
    sid = _uid()
    await memory.push_dialogue(sid, "user", "我想去北京玩")
    await memory.push_dialogue(sid, "assistant", "好的，为您规划")
    result = await memory.get_dialogue(sid)
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    assert "ts" in result[0]


@pytest.mark.asyncio
async def test_dialogue_max_keep(memory: MemoryService):
    sid = _uid()
    for i in range(15):
        await memory.push_dialogue(sid, "user", f"msg{i}", max_keep=5)
    result = await memory.get_dialogue(sid)
    assert len(result) == 5
    assert result[0]["content"] == "msg10"
    assert result[-1]["content"] == "msg14"


@pytest.mark.asyncio
async def test_set_and_get_hot_pois(memory: MemoryService):
    data = [{"name": "故宫", "rating": 4.8}, {"name": "南锣咖啡", "rating": 4.5}]
    await memory.set_hot_pois("北京", "attraction", data, ttl=60)
    result = await memory.get_hot_pois("北京", "attraction")
    assert result == data


@pytest.mark.asyncio
async def test_get_hot_pois_missing(memory: MemoryService):
    result = await memory.get_hot_pois("火星-" + _uid(), "unknown")
    assert result is None


@pytest.mark.asyncio
async def test_sliding_window_pass(memory: MemoryService):
    key = _uid()
    for _ in range(3):
        ok = await memory.sliding_window_check(key, limit=5, window=60)
        assert ok is True


@pytest.mark.asyncio
async def test_sliding_window_reject(memory: MemoryService):
    key = _uid()
    for _ in range(3):
        await memory.sliding_window_check(key, limit=3, window=60)
    ok = await memory.sliding_window_check(key, limit=3, window=60)
    assert ok is False


@pytest.mark.asyncio
async def test_set_and_get_transaction_status(memory: MemoryService):
    txn_id = _uid()
    await memory.set_transaction_status(txn_id, "pending", ttl=60)
    status = await memory.get_transaction_status(txn_id)
    assert status == "pending"


@pytest.mark.asyncio
async def test_get_transaction_status_missing(memory: MemoryService):
    status = await memory.get_transaction_status("txn-missing-" + _uid())
    assert status is None
