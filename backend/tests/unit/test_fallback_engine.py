"""Fallback Engine — 涟漪重排 + Shadow 缓存优先"""

from datetime import datetime, timedelta

import pytest

from app.agents.fallback_engine import FallbackEngine
from app.schemas.plan import (
    POI,
    ExecutionResult,
    FailedSlot,
    PlanDraft,
    PlanSlot,
    TimeRange,
)


@pytest.fixture
def fallback():
    return FallbackEngine()


@pytest.fixture
def draft_with_shadow():
    now = datetime(2026, 5, 13, 14, 0)
    slots = [
        PlanSlot(
            sequence=0,
            poi=POI(id="bj-001", name="故宫", city="北京", type="attraction",
                    lat=39.92, lng=116.40, avg_price=60, rating=4.8),
            time_range=TimeRange(start=now, end=now + timedelta(minutes=60)),
            action="arrive", estimated_cost=60,
            shadow_id="bj-004",
        ),
        PlanSlot(
            sequence=1,
            poi=POI(id="bj-002", name="南锣咖啡", city="北京", type="cafe",
                    lat=39.94, lng=116.40, avg_price=45, rating=4.5),
            time_range=TimeRange(start=now + timedelta(minutes=75),
                                 end=now + timedelta(minutes=135)),
            action="arrive", estimated_cost=45, move_time_min=15,
            shadow_id=None,
        ),
    ]
    return PlanDraft(plan_id="test", slots=slots, total_cost=105, total_time_min=135)


class TestRippleReschedule:
    def test_basic_shift(self, fallback, draft_with_shadow, sample_slots):
        from app.schemas.plan import PlanSlot as PS  # noqa: N817
        slots = [
            PS(sequence=0, poi=POI(**sample_slots[0].poi.model_dump()),
               time_range=TimeRange(start=datetime(2026, 5, 13, 14, 0),
                                    end=datetime(2026, 5, 13, 15, 0)),
               action="arrive", move_time_min=0),
            PS(sequence=1, poi=POI(**sample_slots[1].poi.model_dump()),
               time_range=TimeRange(start=datetime(2026, 5, 13, 14, 30),
                                    end=datetime(2026, 5, 13, 15, 30)),
               action="arrive", move_time_min=30),
        ]
        fallback._ripple_reschedule(slots, 0)
        assert slots[1].time_range.start >= slots[0].time_range.end

    def test_no_shift_when_no_overlap(self, fallback, sample_slots):
        slots = list(sample_slots[:2])
        fallback._ripple_reschedule(slots, 0)
        assert slots[1].time_range.start >= slots[0].time_range.end


class TestFindAlternative:
    def test_shadow_cache_priority(self, fallback, draft_with_shadow):
        result = fallback._find_alternative(draft_with_shadow, 0)
        assert result is not None
        assert result.id == "bj-004"

    def test_fallback_when_no_shadow(self, fallback, draft_with_shadow):
        result = fallback._find_alternative(draft_with_shadow, 1)
        assert result is not None
        assert result.type == "cafe"
        assert result.id != "bj-002"


@pytest.mark.asyncio
async def test_repair_replaces_failed_slot(fallback, draft_with_shadow):
    result = ExecutionResult(
        plan_id="test",
        status="partial_success",
        failed_slots=[
            FailedSlot(slot_index=0, tool_name="book_table",
                       error_code="BOOKING_FULL",
                       error_message="该时段已满", poi_id="bj-001",
                       shadow_candidate=None),
        ],
    )
    revised = await fallback._repair(draft_with_shadow, result, None)
    assert len(revised.diff_patch) == 1
    assert revised.diff_patch[0].slot_index == 0
    assert revised.diff_patch[0].old_poi_id == "bj-001"
