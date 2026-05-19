"""New agent runtime facade for the production refactor."""

from __future__ import annotations

from typing import Any

from app.agent_runtime.state import build_initial_runtime_state, build_request_envelope

GRAPH_VERSION = "v2-refactor-bootstrap"

__all__ = [
    "GRAPH_VERSION",
    "RuntimeEventStore",
    "build_initial_runtime_state",
    "build_plan_graph",
    "build_request_envelope",
]


def __getattr__(name: str) -> Any:
    if name == "RuntimeEventStore":
        from app.agent_runtime.event_store import RuntimeEventStore

        return RuntimeEventStore
    if name == "build_plan_graph":
        from app.agent_runtime.graph import build_plan_graph

        return build_plan_graph
    raise AttributeError(name)
