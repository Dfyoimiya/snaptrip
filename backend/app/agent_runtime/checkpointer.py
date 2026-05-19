"""Default graph checkpointer selection."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver

from app.core.config import settings


def build_default_checkpointer():
    """Choose the best available checkpointer at runtime.

    Handles both old and new langgraph APIs:
    - Old: PostgresSaver.from_conn_string() returns a BaseCheckpointSaver
    - New: PostgresSaver.from_conn_string() returns a context manager
    """

    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        result = PostgresSaver.from_conn_string(settings.effective_database_url)
        if isinstance(result, BaseCheckpointSaver):
            return result
        # Newer langgraph returns a context manager — enter it synchronously
        return result.__enter__()
    except Exception:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
