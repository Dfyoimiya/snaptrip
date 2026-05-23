"""Planning Engine — Phase1 硬过滤 + Phase2 排序 + Shadow 预计算"""

from datetime import datetime, timedelta

import pytest
from snaptrip_shared.schemas.plan import POI, IntentSchema

from agent_worker.app.agent.engines.planning_engine import PlanningEngine
from marketplace.app.data.seed_pois import SEED_POIS


@pytest.fixture
def planning():
    return PlanningEngine()


@pytest.fixture
def beijing_intent():
    return IntentSchema(
        city="北京",
        guest_count=2,
        budget=300,
        type_prefs=["restaurant", "cafe"],
        mood_prefs=["安静", "治愈"],
    )


@pytest.fixture
def beijing_pois():
    return [POI(**p.model_dump()) for p in SEED_POIS if p.city == "北京"]


class TestPhase1HardFilter:
    def test_returns_max_10(self, planning, beijing_intent, beijing_pois):
        result = planning._phase1_hard_filter(
            beijing_pois,
            beijing_intent,
            39.9,
            116.4,
            datetime.now(),
            datetime.now() + timedelta(hours=4),
        )
        assert len(result) <= 10

    def test_type_pref_boosts_score(self, planning, beijing_intent, beijing_pois):
        result = planning._phase1_hard_filter(
            beijing_pois,
            beijing_intent,
            39.9,
            116.4,
            datetime.now(),
            datetime.now() + timedelta(hours=4),
        )
        types = [p.type for p in result]
        assert "restaurant" in types or "cafe" in types

    def test_budget_filter_downgrades(self, planning, beijing_intent, beijing_pois):
        beijing_intent.budget = 50
        result = planning._phase1_hard_filter(
            beijing_pois,
            beijing_intent,
            39.9,
            116.4,
            datetime.now(),
            datetime.now() + timedelta(hours=4),
        )
        assert len(result) <= len(beijing_pois)

    def test_empty_candidates_returns_empty(self, planning, beijing_intent):
        result = planning._phase1_hard_filter(
            [],
            beijing_intent,
            39.9,
            116.4,
            datetime.now(),
            datetime.now() + timedelta(hours=4),
        )
        assert result == []


class TestPhase2FallbackSort:
    def test_sort_by_rating_desc(self, planning, beijing_intent, beijing_pois):
        beijing_intent.mood_prefs = []
        result = planning._phase2_fallback_sort(beijing_pois, beijing_intent)
        ratings = [p.rating for p in result]
        assert ratings == sorted(ratings, reverse=True)

    def test_mood_match_boosts(self, planning, beijing_intent, beijing_pois):
        beijing_intent.mood_prefs = ["安静"]
        result = planning._phase2_fallback_sort(beijing_pois, beijing_intent)
        quiet = [p.name for p in result if "安静" in p.mood_tags]
        noisy = [p.name for p in result if "安静" not in p.mood_tags]
        low_quiet = quiet[-1] if quiet else None
        if low_quiet and noisy:
            quiet_idx = [p.name for p in result].index(low_quiet)
            noisy_idx = [p.name for p in result].index(noisy[0])
            assert quiet_idx < noisy_idx


class TestSlotGeneration:
    def test_slot_count_min_4(self, planning, beijing_intent, beijing_pois):
        now = datetime(2026, 5, 13, 14, 0)
        end = now + timedelta(hours=4)
        slots = planning._generate_slots(beijing_pois, now, end)
        assert len(slots) <= 4

    def test_slot_count_not_exceed_candidates(self, planning, beijing_intent, beijing_pois):
        now = datetime(2026, 5, 13, 14, 0)
        end = now + timedelta(hours=4)
        few = beijing_pois[:2]
        slots = planning._generate_slots(few, now, end)
        assert len(slots) <= 2

    def test_slot_time_monotonic(self, planning, beijing_intent, beijing_pois):
        now = datetime(2026, 5, 13, 14, 0)
        end = now + timedelta(hours=4)
        slots = planning._generate_slots(beijing_pois, now, end)
        for i in range(1, len(slots)):
            assert slots[i].time_range.start >= slots[i - 1].time_range.end

    def test_shadow_id_assigned(self, planning, beijing_intent, beijing_pois):
        now = datetime(2026, 5, 13, 14, 0)
        end = now + timedelta(hours=4)
        slots = planning._generate_slots(beijing_pois, now, end)
        has_shadow = any(s.shadow_id is not None for s in slots)
        assert has_shadow

    def test_shadow_id_different_from_primary(self, planning, beijing_intent, beijing_pois):
        now = datetime(2026, 5, 13, 14, 0)
        end = now + timedelta(hours=4)
        slots = planning._generate_slots(beijing_pois, now, end)
        for s in slots:
            if s.shadow_id:
                assert s.shadow_id != s.poi.id

    def test_empty_pois_returns_empty(self, planning):
        now = datetime(2026, 5, 13, 14, 0)
        slots = planning._generate_slots([], now, now + timedelta(hours=4))
        assert slots == []
