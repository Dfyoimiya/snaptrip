"""Tests for schemas/extract.py — ExtractResult validation logic.

Covers:
  - ExtractResult.is_sufficient() — all cases
  - ExtractResult.missing_fields() — partial data
  - ExtractResult.clarification_question() — question priority
  - ExtractResult.apply_update() — incremental merge (including list merge)
  - UpdateExtractResultInput validation
  - JSON serialization round-trip for LangGraph checkpoint
"""

from __future__ import annotations

from agent.schemas.extract import (
    ExtractResult,
    HardConstraints,
    SoftConstraints,
    UpdateExtractResultInput,
    UserIntent,
    UserRequirements,
)


# ── is_sufficient ────────────────────────────────────────


class TestIsSufficient:
    def test_empty_is_insufficient(self):
        r = ExtractResult()
        assert r.is_sufficient() is False

    def test_fully_populated_is_sufficient(self):
        r = ExtractResult()
        r.intent.city = "北京"
        r.intent.plan_date = "2026-06-15"
        r.intent.time_window_start = "09:00"
        r.intent.time_window_hours = 8.0
        r.intent.guest_count = 2
        r.hard_constraints.budget_max_cny = 500.0
        assert r.is_sufficient() is True

    def test_missing_budget_only(self):
        r = ExtractResult()
        r.intent.city = "上海"
        r.intent.plan_date = "2026-06-15"
        r.intent.time_window_start = "10:00"
        r.intent.time_window_hours = 4.0
        r.intent.guest_count = 3
        # budget_max_cny not set
        assert r.is_sufficient() is False

    def test_missing_one_intent_field(self):
        r = ExtractResult()
        r.intent.city = "深圳"
        r.intent.plan_date = "2026-06-15"
        r.intent.time_window_start = "10:00"
        r.intent.time_window_hours = 4.0
        r.hard_constraints.budget_max_cny = 500.0
        # guest_count not set
        assert r.is_sufficient() is False

    def test_optional_fields_dont_affect_sufficiency(self):
        """Requirements and soft_constraints are optional."""
        r = ExtractResult()
        r.intent.city = "杭州"
        r.intent.plan_date = "2026-06-15"
        r.intent.time_window_start = "09:00"
        r.intent.time_window_hours = 6.0
        r.intent.guest_count = 1
        r.hard_constraints.budget_max_cny = 200.0
        # requirements and soft_constraints left empty
        assert r.is_sufficient() is True


# ── missing_fields ────────────────────────────────────────


class TestMissingFields:
    def test_all_missing(self):
        r = ExtractResult()
        missing = r.missing_fields()
        assert len(missing) == 6  # 5 intent + 1 hard
        assert "intent.city" in missing
        assert "intent.plan_date" in missing
        assert "intent.time_window_start" in missing
        assert "intent.time_window_hours" in missing
        assert "intent.guest_count" in missing
        assert "hard_constraints.budget_max_cny" in missing

    def test_none_missing_when_sufficient(self):
        r = ExtractResult()
        r.intent.city = "北京"
        r.intent.plan_date = "2026-06-15"
        r.intent.time_window_start = "09:00"
        r.intent.time_window_hours = 8.0
        r.intent.guest_count = 2
        r.hard_constraints.budget_max_cny = 500.0
        assert r.missing_fields() == []

    def test_intent_is_none(self):
        """When intent is default-constructed, all fields are None."""
        r = ExtractResult()
        # Verify each intent field is individually accessible as None
        assert r.intent.city is None
        assert r.intent.plan_date is None


# ── clarification_question ────────────────────────────────


class TestClarificationQuestion:
    def test_city_first_priority(self):
        r = ExtractResult()
        q = r.clarification_question()
        assert q is not None
        assert "城市" in q

    def test_date_second_after_city(self):
        r = ExtractResult()
        r.intent.city = "深圳"
        q = r.clarification_question()
        assert q is not None
        assert "日期" in q or "出行" in q

    def test_guest_count_after_time(self):
        r = ExtractResult()
        r.intent.city = "深圳"
        r.intent.plan_date = "2026-06-15"
        r.intent.time_window_start = "09:00"
        r.intent.time_window_hours = 6.0
        # guest_count and budget still missing
        q = r.clarification_question()
        assert q is not None
        assert "人" in q or "几位" in q

    def test_budget_last_priority(self):
        r = ExtractResult()
        r.intent.city = "深圳"
        r.intent.plan_date = "2026-06-15"
        r.intent.time_window_start = "09:00"
        r.intent.time_window_hours = 6.0
        r.intent.guest_count = 2
        q = r.clarification_question()
        assert q is not None
        assert "预算" in q

    def test_no_question_when_sufficient(self):
        r = ExtractResult()
        r.intent.city = "北京"
        r.intent.plan_date = "2026-06-15"
        r.intent.time_window_start = "09:00"
        r.intent.time_window_hours = 8.0
        r.intent.guest_count = 2
        r.hard_constraints.budget_max_cny = 500.0
        assert r.clarification_question() is None


# ── apply_update ──────────────────────────────────────────


class TestApplyUpdate:
    def test_scalar_merge(self):
        r = ExtractResult()
        update = UpdateExtractResultInput(
            intent=UserIntent(city="杭州", guest_count=2),
            hard_constraints=HardConstraints(budget_max_cny=300.0),
        )
        changed = r.apply_update(update)
        assert "intent.city" in changed
        assert "intent.guest_count" in changed
        assert "hard_constraints.budget_max_cny" in changed
        assert r.intent.city == "杭州"
        assert r.intent.guest_count == 2
        assert r.hard_constraints.budget_max_cny == 300.0

    def test_list_merge_preserves_order_and_dedup(self):
        r = ExtractResult()
        u1 = UpdateExtractResultInput(
            soft_constraints=SoftConstraints(preferred_poi_types=["景点", "购物"]),
        )
        r.apply_update(u1)
        u2 = UpdateExtractResultInput(
            soft_constraints=SoftConstraints(preferred_poi_types=["购物", "美食"]),
        )
        changed = r.apply_update(u2)
        # dict.fromkeys preserves first-seen order: 景点, 购物, 美食
        assert r.soft_constraints.preferred_poi_types == ["景点", "购物", "美食"]
        assert len(r.soft_constraints.preferred_poi_types) == 3
        assert "soft_constraints.preferred_poi_types" in changed

    def test_list_merge_idempotent(self):
        r = ExtractResult()
        u = UpdateExtractResultInput(
            soft_constraints=SoftConstraints(preferred_poi_types=["景点"]),
        )
        r.apply_update(u)
        changed = r.apply_update(u)  # same update again
        assert changed == []  # no changes because lists are identical
        assert r.soft_constraints.preferred_poi_types == ["景点"]

    def test_confidence_update(self):
        r = ExtractResult()
        update = UpdateExtractResultInput(confidence=0.85)
        changed = r.apply_update(update)
        assert "confidence" in changed
        assert r.confidence == 0.85

    def test_requirements_list_merge(self):
        r = ExtractResult()
        u1 = UpdateExtractResultInput(
            requirements=UserRequirements(must_have_cuisine=["川菜"]),
        )
        r.apply_update(u1)
        u2 = UpdateExtractResultInput(
            requirements=UserRequirements(must_have_cuisine=["粤菜"]),
        )
        r.apply_update(u2)
        assert set(r.requirements.must_have_cuisine) == {"川菜", "粤菜"}

    def test_hard_constraints_list_merge(self):
        r = ExtractResult()
        u1 = UpdateExtractResultInput(
            hard_constraints=HardConstraints(dietary_restrictions=["清真"]),
        )
        r.apply_update(u1)
        u2 = UpdateExtractResultInput(
            hard_constraints=HardConstraints(dietary_restrictions=["素食"]),
        )
        r.apply_update(u2)
        assert set(r.hard_constraints.dietary_restrictions) == {"清真", "素食"}

    def test_non_list_field_does_not_overwrite(self):
        """Scalar fields should be overwritten, not merged."""
        r = ExtractResult()
        u1 = UpdateExtractResultInput(intent=UserIntent(city="北京"))
        r.apply_update(u1)
        assert r.intent.city == "北京"

        u2 = UpdateExtractResultInput(intent=UserIntent(city="上海"))
        r.apply_update(u2)
        assert r.intent.city == "上海"  # overwritten

    def test_none_fields_not_applied(self):
        """Fields that are None in the update should not touch existing values."""
        r = ExtractResult()
        r.intent.city = "北京"
        update = UpdateExtractResultInput(
            intent=UserIntent(guest_count=3),  # city is None here
        )
        changed = r.apply_update(update)
        assert r.intent.city == "北京"  # unchanged
        assert r.intent.guest_count == 3  # updated
        assert "intent.city" not in changed


# ── Serialization ─────────────────────────────────────────


class TestSerialization:
    def test_json_round_trip(self):
        """LangGraph checkpoint uses JSON serialization."""
        r = ExtractResult()
        r.intent.city = "北京"
        r.intent.guest_count = 2
        r.hard_constraints.budget_max_cny = 500.0
        r.soft_constraints.preferred_poi_types = ["景点", "购物"]
        r.confidence = 0.9

        json_str = r.model_dump_json()
        restored = ExtractResult.model_validate_json(json_str)

        assert restored.intent.city == "北京"
        assert restored.intent.guest_count == 2
        assert restored.hard_constraints.budget_max_cny == 500.0
        assert restored.soft_constraints.preferred_poi_types == ["景点", "购物"]
        assert restored.confidence == 0.9

    def test_model_dump_exclude_none(self):
        r = ExtractResult()
        r.intent.city = "杭州"
        r.soft_constraints.preferred_poi_types = ["景点"]
        dumped = r.model_dump(exclude_none=True)
        # intent sub-model — only city is set
        assert dumped["intent"] == {"city": "杭州"}
        # soft_constraints — only preferred_poi_types (lists with items are included)
        assert "soft_constraints" in dumped
        assert dumped["soft_constraints"]["preferred_poi_types"] == ["景点"]
        # empty default lists remain (not None, so not excluded)
        assert dumped["hard_constraints"]["dietary_restrictions"] == []

    def test_default_factory_lists(self):
        """Default factory lists should be empty, not shared instances."""
        r1 = ExtractResult()
        r2 = ExtractResult()
        r1.requirements.must_have_cuisine.append("川菜")
        assert r2.requirements.must_have_cuisine == []


# ── Enums ────────────────────────────────────────────────


class TestEnums:
    def test_scene_type_values(self):
        from agent.schemas.extract import SceneType
        assert SceneType.FAMILY == "family"
        assert SceneType.FRIENDS == "friends"
        assert SceneType.COUPLE == "couple"
        assert SceneType.SOLO == "solo"

    def test_budget_preference_values(self):
        from agent.schemas.extract import BudgetPreference
        assert BudgetPreference.ECONOMY == "economy"
        assert BudgetPreference.MID == "mid"
        assert BudgetPreference.LUXURY == "luxury"

    def test_travel_pace_values(self):
        from agent.schemas.extract import TravelPace
        assert TravelPace.RELAXED == "relaxed"
        assert TravelPace.BALANCED == "balanced"
        assert TravelPace.FAST == "fast"
