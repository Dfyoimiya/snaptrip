"""Pytest fixtures —— sample data for unit tests.

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.state import PlanStateMachine
from app.schemas.plan import (
    POI,
    IntentSchema,
    PlanDraft,
    PlanSlot,
    TimeRange,
)


@pytest.fixture
def sample_pois():
    return [
        POI(id="bj-1", name="故宫", city="北京", type="attraction", lat=39.92, lng=116.40,
            mood_tags=["历史文化", "亲子"], avg_price=60, rating=4.8),
        POI(id="bj-2", name="南锣咖啡", city="北京", type="cafe", lat=39.94, lng=116.40,
            mood_tags=["治愈", "安静"], avg_price=45, rating=4.5),
        POI(id="bj-3", name="四季民福", city="北京", type="restaurant", lat=39.91, lng=116.41,
            mood_tags=["聚餐", "热门"], avg_price=150, rating=4.7),
        POI(id="bj-4", name="798艺术区", city="北京", type="attraction", lat=39.98, lng=116.50,
            mood_tags=["文艺", "拍照"], avg_price=0, rating=4.4),
        POI(id="cq-1", name="洞子火锅", city="重庆", type="restaurant", lat=29.56, lng=106.57,
            mood_tags=["辣", "热闹"], avg_price=80, rating=4.7),
    ]


@pytest.fixture
def sample_intent():
    return IntentSchema(
        city="北京", guest_count=2, budget=300,
        type_prefs=["restaurant", "cafe"],
        mood_prefs=["安静", "治愈"],
        scene_type="friends",
    )


@pytest.fixture
def sample_slots(sample_pois):
    now = datetime(2026, 5, 13, 14, 0)
    return [
        PlanSlot(sequence=0, poi=sample_pois[1],
                 time_range=TimeRange(start=now, end=now + timedelta(minutes=60)),
                 action="arrive", estimated_cost=45, confidence=0.8),
        PlanSlot(sequence=1, poi=sample_pois[2],
                 time_range=TimeRange(start=now + timedelta(minutes=75), end=now + timedelta(minutes=135)),
                 action="book_table", estimated_cost=150, confidence=0.7, move_time_min=15),
        PlanSlot(sequence=2, poi=sample_pois[0],
                 time_range=TimeRange(start=now + timedelta(minutes=155), end=now + timedelta(minutes=215)),
                 action="arrive", estimated_cost=60, confidence=0.65, move_time_min=20),
    ]


@pytest.fixture
def sample_draft(sample_slots):
    return PlanDraft(
        plan_id="test-plan-1",
        slots=sample_slots,
        total_cost=255,
        total_time_min=215,
        confidence=0.7,
        version=1,
    )


@pytest.fixture
def state_machine():
    return PlanStateMachine()
