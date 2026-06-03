"""Tests for CompensationAction and CompensationRegistry."""

from __future__ import annotations

import asyncio

import pytest

from agent.tools.transaction.compensation import CompensationAction, CompensationRegistry


class TestCompensationAction:
    """Tests for CompensationAction."""

    async def _noop(self) -> None:
        pass

    def test_action_creation(self):
        """A CompensationAction can be created."""
        action = CompensationAction(
            action_id="cancel:ord-1",
            tool_name="mock_order",
            description="Cancel order ord-1",
            execute=self._noop,
        )
        assert action.action_id == "cancel:ord-1"
        assert action.tool_name == "mock_order"
        assert action.description == "Cancel order ord-1"
        assert action.max_retries == 3

    def test_hash_based_on_action_id(self):
        """CompensationAction hash is based on action_id."""
        a1 = CompensationAction(
            action_id="id-1", tool_name="t", description="d1", execute=self._noop,
        )
        a2 = CompensationAction(
            action_id="id-1", tool_name="other", description="d2", execute=self._noop,
        )
        assert hash(a1) == hash(a2)

    def test_equality_based_on_action_id(self):
        """CompensationAction equality is based on action_id."""
        a1 = CompensationAction(
            action_id="id-1", tool_name="t", description="d1", execute=self._noop,
        )
        a2 = CompensationAction(
            action_id="id-1", tool_name="other", description="d2", execute=self._noop,
        )
        assert a1 == a2

    def test_not_equal_to_non_action(self):
        a = CompensationAction(
            action_id="id-1", tool_name="t", description="d", execute=self._noop,
        )
        assert a != "id-1"
        assert a != 42


class TestCompensationRegistry:
    """Tests for CompensationRegistry."""

    @pytest.mark.asyncio
    async def test_register_and_rollback(self):
        """Register actions and rollback in LIFO order."""

        executed: list[str] = []

        async def make_exec(order_id: str):
            async def _exec() -> None:
                executed.append(order_id)
            return _exec

        reg = CompensationRegistry()
        reg.register(CompensationAction(
            action_id="a1", tool_name="t", description="First",
            execute=await make_exec("a1"),
        ))
        reg.register(CompensationAction(
            action_id="a2", tool_name="t", description="Second",
            execute=await make_exec("a2"),
        ))
        reg.register(CompensationAction(
            action_id="a3", tool_name="t", description="Third",
            execute=await make_exec("a3"),
        ))

        failed = await reg.rollback_all()
        assert failed == []  # All succeeded
        assert executed == ["a3", "a2", "a1"]  # LIFO order

    @pytest.mark.asyncio
    async def test_deduplication_on_action_id(self):
        """Registering same action_id twice is a no-op."""
        async def _noop() -> None:
            pass

        reg = CompensationRegistry()
        reg.register(CompensationAction(
            action_id="dup", tool_name="t", description="d", execute=_noop,
        ))
        reg.register(CompensationAction(
            action_id="dup", tool_name="t", description="d", execute=_noop,
        ))
        assert len(reg._actions) == 1

    @pytest.mark.asyncio
    async def test_rollback_skips_already_executed(self):
        """Actions already executed are skipped on subsequent rollbacks."""
        async def _noop() -> None:
            pass

        reg = CompensationRegistry()
        reg.register(CompensationAction(
            action_id="a1", tool_name="t", description="d", execute=_noop,
        ))

        await reg.rollback_all()
        # Second rollback should skip a1
        failed = await reg.rollback_all()
        assert failed == []

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Actions are retried up to max_retries on failure."""
        call_count = 0

        async def _fail_then_succeed() -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("fail")

        reg = CompensationRegistry()
        reg.register(CompensationAction(
            action_id="retry-1", tool_name="t", description="retry",
            execute=_fail_then_succeed, max_retries=3,
        ))

        failed = await reg.rollback_all()
        assert failed == []
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_permanent_failure(self):
        """Action that always fails returns its action_id in failed list."""
        async def _always_fail() -> None:
            raise RuntimeError("permanent failure")

        reg = CompensationRegistry()
        reg.register(CompensationAction(
            action_id="fail-1", tool_name="t", description="always fails",
            execute=_always_fail, max_retries=2,
        ))

        failed = await reg.rollback_all()
        assert failed == ["fail-1"]

    @pytest.mark.asyncio
    async def test_empty_registry_rollback(self):
        """Rolling back an empty registry succeeds."""
        reg = CompensationRegistry()
        failed = await reg.rollback_all()
        assert failed == []

    @pytest.mark.asyncio
    async def test_rollback_respects_lifo_order_integration(self):
        """Complex scenario: some succeed, some fail, order preserved."""

        results: list[str] = []

        async def _record(name: str):
            async def _exec() -> None:
                results.append(name)
            return _exec

        reg = CompensationRegistry()
        reg.register(CompensationAction(
            action_id="c1", tool_name="t", description="first",
            execute=await _record("c1"),
        ))
        reg.register(CompensationAction(
            action_id="c2", tool_name="t", description="second",
            execute=await _record("c2"), max_retries=2,
        ))

        # c2 fails once, succeeds on retry
        call_count2 = 0
        async def _flaky_c2() -> None:
            nonlocal call_count2
            call_count2 += 1
            if call_count2 == 1:
                raise RuntimeError("fail")
            results.append("c2")

        # Override c2's execute
        reg._actions[1].execute = _flaky_c2

        _ = await reg._execute_with_retry(reg._actions[1])
        assert call_count2 == 2  # One failure + one success
