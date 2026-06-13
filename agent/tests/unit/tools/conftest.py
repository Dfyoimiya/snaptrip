"""Shared fixtures for SmartDay tool layer tests.

All fixtures are function-scoped for test isolation.
External services (Amap MCP, REST API) are mocked at the adapter level.
"""

from __future__ import annotations

import asyncio
import random
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest

from agent.tools.harness.context import SessionContext, ToolExecutionContext
from agent.tools.tracing.audit_log import AuditStore
from agent.tools.transaction.compensation import CompensationAction, CompensationRegistry
from agent.tools.transaction.context import TransactionContext, TxStatus
from agent.tools.registry.registry import ToolRegistry
from agent.tools.implementations.base import ToolResult


# ═══════════════════════════════════════════════════════════════
# General-purpose fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def registry() -> ToolRegistry:
    """An empty ToolRegistry for tests that need to register tools."""
    return ToolRegistry()


def _make_mock_tool(name="test_tool", read_only=False, cost_model="free"):
    """Helper to create a MagicMock that satisfies SmartDayBaseTool interface."""
    from pydantic import BaseModel

    class DummySchema(BaseModel):
        lat: float = 0.0

    tool = MagicMock()
    tool.name = name
    tool.description = f"{name}. Use it."
    tool.args_schema = DummySchema
    tool.is_read_only = read_only
    tool.cost_model = cost_model
    tool.tool_timeout = 5.0
    return tool


@pytest.fixture
def make_mock_tool():
    """Factory fixture for mock tool creation."""
    return _make_mock_tool


@pytest.fixture
def mock_tool() -> MagicMock:
    """A generic mock SmartDayBaseTool."""
    return _make_mock_tool()


@pytest.fixture
def session_ctx() -> SessionContext:
    """A SessionContext with a known user_id for tests that require auth."""
    return SessionContext(
        session_id="test-session-001",
        user_id="test-user-001",
        amap_api_key="test-key",
    )


@pytest.fixture
def session_ctx_unauthenticated() -> SessionContext:
    """A SessionContext without user_id (for auth-negative tests)."""
    return SessionContext(session_id="test-session-002", user_id="")


@pytest.fixture
def audit_store() -> AuditStore:
    return AuditStore()


@pytest.fixture
def comp_registry() -> CompensationRegistry:
    return CompensationRegistry()


@pytest.fixture
def tx_ctx(session_ctx: SessionContext) -> TransactionContext:
    return TransactionContext.new(session_id=session_ctx.session_id)


@pytest.fixture
def active_tx_ctx(session_ctx: SessionContext) -> TransactionContext:
    tx = TransactionContext.new(session_id=session_ctx.session_id)
    tx.begin_call(tool_name="test_tool", args_hash="abc123")
    return tx


# ═══════════════════════════════════════════════════════════════
# Tool execution context fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def exec_ctx(session_ctx: SessionContext) -> ToolExecutionContext:
    """A basic ToolExecutionContext for hook testing."""
    return ToolExecutionContext(
        tool_name="test_tool",
        args={"key": "value"},
        session_ctx=session_ctx,
    )


@pytest.fixture
def exec_ctx_with_tx(
    session_ctx: SessionContext,
    tx_ctx: TransactionContext,
) -> ToolExecutionContext:
    """A ToolExecutionContext with an attached transaction."""
    return ToolExecutionContext(
        tool_name="test_tool",
        args={"key": "value"},
        session_ctx=session_ctx,
        tx_ctx=tx_ctx,
    )


# ═══════════════════════════════════════════════════════════════
# Mock async compensation action
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def noop_comp_action() -> CompensationAction:
    async def _noop() -> None:
        pass

    return CompensationAction(
        action_id="noop-1",
        tool_name="test_tool",
        description="No-op compensation",
        execute=_noop,
    )


# ═══════════════════════════════════════════════════════════════
# Seed-controlled random for mock tools
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def freeze_random():
    """Freeze random for deterministic mock-tool behaviour."""
    random.seed(42)
    yield
    random.seed()


@pytest.fixture
def force_random_failure():
    """Patch random.random to return < 0.05 so mock tools fail."""
    with patch("random.random", return_value=0.03):
        yield


# ═══════════════════════════════════════════════════════════════
# Event loop fixture
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def event_loop():
    """Create a fresh event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
