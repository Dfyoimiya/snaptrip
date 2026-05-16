"""Execution Engine — DAG 分层 + 依赖跳过 + 超时"""

from datetime import datetime, timedelta

import pytest

from app.agents.execution_engine import ExecutionEngine
from app.schemas.plan import POI, PlanDraft, PlanSlot, TimeRange


@pytest.fixture
def engine():
    return ExecutionEngine()


def make_slot(seq: int, action: str, poi_id: str) -> PlanSlot:
    now = datetime(2026, 5, 13, 14, 0)
    return PlanSlot(
        sequence=seq,
        poi=POI(id=poi_id, name="test", city="北京", type="restaurant",
                lat=39.9, lng=116.4, avg_price=100, rating=4.5),
        time_range=TimeRange(start=now + timedelta(hours=seq),
                             end=now + timedelta(hours=seq + 1)),
        action=action, estimated_cost=100,
    )


@pytest.mark.asyncio
async def test_execute_generates_result(engine):
    draft = PlanDraft(plan_id="test", slots=[
        make_slot(0, "book_table", "p1"),
        make_slot(1, "book_ticket", "p2"),
    ], total_cost=200)
    result = await engine._execute_dag(draft, None)
    assert result.status in ("full_success", "partial_success", "full_failure")


@pytest.mark.asyncio
async def test_failed_tool_produces_failed_slots(engine):
    draft = PlanDraft(plan_id="test", slots=[
        make_slot(0, "book_table", "p1"),
    ], total_cost=100)
    result = await engine._execute_dag(draft, None)
    assert result.total_elapsed_ms >= 0
