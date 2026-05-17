"""Tool DAG — 工具注册表 + 拓扑排序 + 熔断器"""

from datetime import datetime, timedelta

import pytest

from app.schemas.plan import POI, PlanSlot, TimeRange
from app.schemas.tool import TOOL_REGISTRY
from app.services.tool_dag import ToolDAGScheduler, build_execution_layers


def make_slot(seq: int, action: str, poi_id: str) -> PlanSlot:
    now = datetime(2026, 5, 13, 14, 0)
    return PlanSlot(
        sequence=seq,
        poi=POI(
            id=poi_id, name="test", city="北京", type="restaurant",
            lat=39.9, lng=116.4, avg_price=100, rating=4.5,
        ),
        time_range=TimeRange(
            start=now + timedelta(hours=seq),
            end=now + timedelta(hours=seq + 1),
        ),
        action=action, estimated_cost=100,
    )


class TestToolRegistry:
    def test_all_tools_registered(self):
        expected = {
            "search_poi", "get_user_profile", "check_queue",
            "check_availability", "check_child_facility",
            "calculate_route", "book_table", "book_ticket",
            "order", "notify",
        }
        assert set(TOOL_REGISTRY.keys()) == expected

    def test_book_table_depends_on_check_queue(self):
        assert "check_queue" in TOOL_REGISTRY["book_table"].dependencies

    def test_book_table_depends_on_check_availability(self):
        assert "check_availability" in TOOL_REGISTRY["book_table"].dependencies

    def test_l0_no_dependencies(self):
        assert TOOL_REGISTRY["search_poi"].dependencies == []

    def test_l3_depends_on_l2_all(self):
        deps = TOOL_REGISTRY["notify"].dependencies
        assert "book_table" in deps
        assert "book_ticket" in deps
        assert "order" in deps

    def test_tool_definition_has_input_schema(self):
        assert "poi_id" in TOOL_REGISTRY["book_table"].input_schema["properties"]

    def test_fallback_policy_values(self):
        assert TOOL_REGISTRY["book_table"].fallback_policy == "abort"
        assert TOOL_REGISTRY["order"].fallback_policy == "continue"
        assert TOOL_REGISTRY["search_poi"].fallback_policy == "degrade"


class TestBuildLayers:
    def test_layers_grouped_correctly(self):
        slots = [
            make_slot(0, "book_table", "p1"),
            make_slot(1, "search_poi", "p2"),
        ]
        layers = build_execution_layers(slots)
        assert 0 in layers
        assert 2 in layers

    def test_same_layer_parallel(self):
        slots = [
            make_slot(0, "book_table", "p1"),
            make_slot(1, "book_ticket", "p2"),
        ]
        layers = build_execution_layers(slots)
        assert len(layers.get(2, [])) == 2


class TestCircuitBreaker:
    def test_starts_closed(self):
        scheduler = ToolDAGScheduler()
        assert "book_table" not in scheduler.circuit_open

    def test_failure_count_inits_zero(self):
        scheduler = ToolDAGScheduler()
        assert scheduler.failure_counts.get("book_table", 0) == 0
