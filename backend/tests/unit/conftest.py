"""Shared fixtures for unit tests.

Provides a reusable mock_db fixture and factory helpers used across
service test modules. Reduces duplication in individual test files.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


async def _refresh_fake(obj: object) -> None:
    """Simulate flush/refresh generating the primary key."""
    obj.id = uuid4()  # type: ignore[attr-defined]


@pytest.fixture
def mock_db() -> AsyncSession:
    """Standard async DB session mock used by all service tests."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock(side_effect=_refresh_fake)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    db.get = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_exec_result() -> MagicMock:
    """Standard execute result mock returning a single row."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = MagicMock()
    return result


def make_mock_exec_result(rowcount: int = 1) -> MagicMock:
    """Create an execute result with given rowcount (for delete/update operations)."""
    result = MagicMock()
    result.rowcount = rowcount
    return result


def make_count_and_list_mocks(
    total: int = 1,
    items: list | None = None,
) -> list[MagicMock]:
    """Create count + list execute result mocks for paginated queries."""
    count_result = MagicMock()
    count_result.scalar.return_value = total

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = items or []

    return [count_result, list_result]
