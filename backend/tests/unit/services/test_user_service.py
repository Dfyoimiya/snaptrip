"""Unit tests for user_service utility functions.

Tests trigger_preference_embedding_update with and without Celery available.
Uses sys.modules patching because the function imports
``app.tasks.plan_tasks`` at runtime inside a try/except.

Author: SnapTrip Team
Date: 2026-06-08
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
#  trigger_preference_embedding_update
# ---------------------------------------------------------------------------


class TestTriggerPreferenceEmbeddingUpdate:
    """Tests for the trigger_preference_embedding_update utility."""

    def test_happy_path_returns_task_id(self):
        """When the module is importable, returns task.id after delay."""
        fake_task = MagicMock()
        fake_task.id = "abc-123-def"

        fake_rebuild = MagicMock()
        fake_rebuild.delay.return_value = fake_task

        fake_module = MagicMock()
        fake_module.rebuild_user_preference_embedding = fake_rebuild

        with patch.dict("sys.modules", {"app.tasks.plan_tasks": fake_module}):
            from app.services.user_service import trigger_preference_embedding_update

            result = trigger_preference_embedding_update("user-001")

            assert result == "abc-123-def"
            fake_rebuild.delay.assert_called_once_with("user-001")

    def test_celery_unavailable_returns_none(self):
        """When the module cannot be imported, returns None gracefully."""
        # Remove the module from sys.modules so the import raises
        with patch.dict("sys.modules", clear=False):
            sys.modules.pop("app.tasks.plan_tasks", None)
            from app.services.user_service import trigger_preference_embedding_update

            result = trigger_preference_embedding_update("user-001")

            assert result is None

    def test_celery_raises_runtime_error_returns_none(self):
        """When delay() raises a runtime exception, returns None."""
        fake_rebuild = MagicMock()
        fake_rebuild.delay.side_effect = RuntimeError("Broker connection failed")

        fake_module = MagicMock()
        fake_module.rebuild_user_preference_embedding = fake_rebuild

        with patch.dict("sys.modules", {"app.tasks.plan_tasks": fake_module}):
            from app.services.user_service import trigger_preference_embedding_update

            result = trigger_preference_embedding_update("user-001")

            assert result is None

    def test_various_user_id_formats(self):
        """Works with different user_id formats (UUID string, numeric, etc.)."""
        fake_task = MagicMock()
        fake_task.id = "task-uuid"

        fake_rebuild = MagicMock()
        fake_rebuild.delay.return_value = fake_task

        fake_module = MagicMock()
        fake_module.rebuild_user_preference_embedding = fake_rebuild

        with patch.dict("sys.modules", {"app.tasks.plan_tasks": fake_module}):
            from app.services.user_service import trigger_preference_embedding_update

            # UUID string
            assert trigger_preference_embedding_update(
                "550e8400-e29b-41d4-a716-446655440000"
            ) == "task-uuid"

            # numeric string
            assert trigger_preference_embedding_update("12345") == "task-uuid"

            # email-like
            assert trigger_preference_embedding_update(
                "user@example.com"
            ) == "task-uuid"

            assert fake_rebuild.delay.call_count == 3

    def test_empty_string_user_id(self):
        """Empty string user_id still passes through to Celery task."""
        fake_task = MagicMock()
        fake_task.id = "task-empty"

        fake_rebuild = MagicMock()
        fake_rebuild.delay.return_value = fake_task

        fake_module = MagicMock()
        fake_module.rebuild_user_preference_embedding = fake_rebuild

        with patch.dict("sys.modules", {"app.tasks.plan_tasks": fake_module}):
            from app.services.user_service import trigger_preference_embedding_update

            result = trigger_preference_embedding_update("")

            assert result == "task-empty"
            fake_rebuild.delay.assert_called_once_with("")
