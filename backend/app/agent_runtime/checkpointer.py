"""Default graph checkpointer selection."""

from __future__ import annotations

from app.core.config import settings


def build_default_checkpointer():
    """Choose the best available checkpointer at runtime."""

    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        return PostgresSaver.from_conn_string(settings.effective_database_url)
    except Exception:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
