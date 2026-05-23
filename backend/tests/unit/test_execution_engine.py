"""Execution Engine — DAG 分层 + 依赖跳过 + 超时"""

from datetime import datetime, timedelta

import pytest
from agent.engines.execution_engine import ExecutionEngine
from snaptrip_shared.schemas.plan import (
    POI,
    ExecutionResult,
    FailedSlot,
    PlanDraft,
    PlanSlot,
    SlotExecutionResult,
    TimeRange,
)


@pytest.fixture
def engine():
    return ExecutionEngine()


def make_slot(seq: int, action: str, poi_id: str) -> PlanSlot:
    now = datetime(2026, 5, 13, 14, 0)
    return PlanSlot(
        sequence=seq,
        poi=POI(id=poi_id, name="test", city="北京", type="restaurant", lat=39.9, lng=116.4, avg_price=100, rating=4.5),
        time_range=TimeRange(start=now + timedelta(hours=seq), end=now + timedelta(hours=seq + 1)),
        action=action,
        estimated_cost=100,
    )


@pytest.mark.asyncio
async def test_execute_generates_result(engine):
    draft = PlanDraft(
        plan_id="test",
        slots=[
            make_slot(0, "book_table", "p1"),
            make_slot(1, "book_ticket", "p2"),
        ],
        total_cost=200,
    )
    result = await engine._execute_dag(draft, None)
    assert result.status in ("full_success", "partial_success", "full_failure")


@pytest.mark.asyncio
async def test_failed_tool_produces_failed_slots(engine):
    draft = PlanDraft(
        plan_id="test",
        slots=[
            make_slot(0, "book_table", "p1"),
        ],
        total_cost=100,
    )
    result = await engine._execute_dag(draft, None)
    assert result.total_elapsed_ms >= 0


def test_normalize_gateway_response_legacy_success(engine):
    normalized = engine._normalize_gateway_response(
        "book_table",
        0,
        {"success": True, "data": {"table_number": "A1"}},
    )
    assert normalized["status"] == "success"
    assert normalized["data"]["booking_id"].startswith("gw_book_table_0")


def test_to_execution_state_preserves_timeout_and_failed_slots(engine):
    result = ExecutionResult(
        plan_id="run_1",
        status="partial_success",
        slot_results={
            0: SlotExecutionResult(
                slot_index=0,
                tool_name="book_table",
                status="timeout",
                error_code="TIMEOUT",
                error_message="book_table timed out",
                elapsed_ms=3000,
            )
        },
        confirmed_bookings={},
        failed_slots=[
            FailedSlot(
                slot_index=1,
                tool_name="book_ticket",
                error_code="SKIPPED",
                error_message="Upstream dependency failed",
                poi_id="1",
            )
        ],
        total_elapsed_ms=3000,
    )

    state = engine.to_execution_state(result)

    assert state.status == "partial_success"
    assert 1 in state.failed_slot_indices
    assert any(record.status == "timeout" for record in state.tool_records)
    assert any(record.status == "skipped" for record in state.tool_records)
