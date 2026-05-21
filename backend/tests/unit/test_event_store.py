"""Runtime event store tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from agent_worker.app.agent.events.store import RuntimeEventStore
from agent_worker.app.agent.schemas.events import RuntimeEvent


def _event(event_id: str, event_type: str = "node_started") -> RuntimeEvent:
    return RuntimeEvent(
        event_id=event_id,
        run_id="run_1",
        plan_id="plan_1",
        node_name="planning_engine",
        event_type=event_type,
        timestamp=datetime.now(UTC),
        payload={"slot_count": 2},
    )


@pytest.mark.asyncio
async def test_event_store_emit_and_list():
    store = RuntimeEventStore()
    await store.emit(_event("evt_1"))

    events = await store.list_by_plan("plan_1")

    assert len(events) == 1
    assert events[0].event_id == "evt_1"


@pytest.mark.asyncio
async def test_event_store_wait_for_new_events():
    store = RuntimeEventStore()

    async def delayed_emit():
        await asyncio.sleep(0.05)
        await store.emit(_event("evt_2", "plan_completed"))

    task = asyncio.create_task(delayed_emit())
    events = await store.wait_for_events("plan_1", after_index=0, timeout_s=1.0)
    await task

    assert len(events) == 1
    assert events[0].event_type == "plan_completed"
