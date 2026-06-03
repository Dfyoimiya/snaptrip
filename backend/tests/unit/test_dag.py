"""DAG 调度 + 熔断器 + Saga 单元测试。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.schemas.tool import TOOL_REGISTRY, ToolInvocation, ToolResult
from app.services.circuit_breaker import CircuitBreaker, CircuitState
from app.services.saga import SagaCoordinator
from app.services.tool_dag import (
    ToolDAGExecutor,
    ToolDAGScheduler,
    build_execution_layers,
    topological_layers,
)


class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.tool_name == "test"

    @pytest.mark.asyncio
    async def test_trip_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60)
        for _ in range(2):
            r = await cb.call(_always_fail)
            assert r.status == "failure"
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_reject_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)
        await cb.call(_always_fail)
        assert cb.state == CircuitState.OPEN
        r = await cb.call(_always_ok)
        assert r.status == "failure"
        assert r.error_code == "CIRCUIT_OPEN"

    @pytest.mark.asyncio
    async def test_success_resets_counter(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
        await cb.call(_always_fail)
        await cb.call(_always_fail)
        assert cb.state == CircuitState.CLOSED
        await cb.call(_always_ok)
        assert cb.state == CircuitState.CLOSED


class TestTopologicalLayers:
    def test_simple_dag(self):
        inv = [
            ToolInvocation(tool_name="search_poi", invocation_id="1", dependencies=[]),
            ToolInvocation(tool_name="check_queue", invocation_id="2", dependencies=["1"]),
            ToolInvocation(tool_name="book_table", invocation_id="3", dependencies=["2"]),
        ]
        layers = topological_layers(inv)
        assert len(layers) == 3
        assert layers[0][0].invocation_id == "1"
        assert layers[1][0].invocation_id == "2"
        assert layers[2][0].invocation_id == "3"

    def test_parallel_layer(self):
        inv = [
            ToolInvocation(tool_name="search_poi", invocation_id="1", dependencies=[]),
            ToolInvocation(tool_name="get_user_profile", invocation_id="2", dependencies=[]),
        ]
        layers = topological_layers(inv)
        assert len(layers) == 1
        assert len(layers[0]) == 2

    def test_cycle_detection(self):
        inv = [
            ToolInvocation(tool_name="a", invocation_id="1", dependencies=["2"]),
            ToolInvocation(tool_name="b", invocation_id="2", dependencies=["1"]),
        ]
        with pytest.raises(ValueError, match="循环依赖"):
            topological_layers(inv)

    def test_complex_dag(self):
        inv = [
            ToolInvocation(tool_name="L0a", invocation_id="l0a", dependencies=[]),
            ToolInvocation(tool_name="L0b", invocation_id="l0b", dependencies=[]),
            ToolInvocation(tool_name="L1a", invocation_id="l1a", dependencies=["l0a"]),
            ToolInvocation(tool_name="L1b", invocation_id="l1b", dependencies=["l0a", "l0b"]),
            ToolInvocation(tool_name="L2", invocation_id="l2", dependencies=["l1a", "l1b"]),
        ]
        layers = topological_layers(inv)
        assert len(layers) == 3
        assert len(layers[0]) == 2
        assert len(layers[1]) == 2
        assert len(layers[2]) == 1


class TestSaga:
    @pytest.mark.asyncio
    async def test_compensate_empty(self):
        saga = SagaCoordinator()
        errors = await saga.compensate()
        assert errors == []

    @pytest.mark.asyncio
    async def test_compensate_reverse_order(self):
        saga = SagaCoordinator()
        called: list[str] = []

        async def comp(_tool: str, _params: dict) -> None:
            called.append(_tool)

        saga.register_compensation("a", comp)
        saga.register_compensation("b", comp)

        inv_a = ToolInvocation(tool_name="a")
        inv_b = ToolInvocation(tool_name="b")
        saga.record_step(inv_a, ToolResult(invocation_id=inv_a.invocation_id))
        saga.record_step(inv_b, ToolResult(invocation_id=inv_b.invocation_id))

        await saga.compensate()
        assert called == ["b", "a"]  # 逆序


class TestDAGScheduler:
    def test_build_layers_from_slots(self):
        from datetime import datetime, timedelta

        from app.schemas.plan import POI, PlanSlot, TimeRange

        slots = [
            PlanSlot(
                sequence=0,
                poi=POI(id="p1", name="t", city="北京", type="restaurant", lat=39.9, lng=116.4),
                time_range=TimeRange(start=datetime(2026, 5, 13, 14, 0), end=datetime(2026, 5, 13, 15, 0)),
                action="book_table",
            ),
            PlanSlot(
                sequence=1,
                poi=POI(id="p2", name="t", city="北京", type="cafe", lat=39.9, lng=116.4),
                time_range=TimeRange(start=datetime(2026, 5, 13, 14, 0), end=datetime(2026, 5, 13, 15, 0)),
                action="search_poi",
            ),
        ]
        layers = build_execution_layers(slots)
        assert 0 in layers or 2 in layers


class TestDAGExecutor:
    @pytest.mark.asyncio
    async def test_execute_without_memory(self):
        executor = ToolDAGExecutor(memory=None)
        inv = [
            ToolInvocation(tool_name="search_poi", invocation_id="1", params={"lat": 39.9, "lng": 116.4}),
        ]
        result = await executor.execute(inv)
        assert result["transaction_id"] is not None
        assert "results" in result

    @pytest.mark.asyncio
    async def test_dag_with_deps(self):
        executor = ToolDAGExecutor(memory=None)
        inv = [
            ToolInvocation(tool_name="search_poi", invocation_id="a", dependencies=[]),
            ToolInvocation(tool_name="check_queue", invocation_id="b", dependencies=["a"],
                          params={"poi_id": "bj-001"}),
        ]
        result = await executor.execute(inv)
        assert len(result["results"]) == 2


async def _always_fail() -> ToolResult:
    return ToolResult(invocation_id="x", status="failure", error_code="TEST_FAIL")


async def _always_ok() -> ToolResult:
    return ToolResult(invocation_id="x", status="success", data={"ok": True})
