"""Facade over the existing graph while the production runtime is migrated."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agent_runtime.checkpointer import build_default_checkpointer
from app.agents.graph import build_plan_graph as _build_legacy_plan_graph

if TYPE_CHECKING:
    from app.agent.runtime import AgentRuntime

GRAPH_VERSION = "v2-refactor-bootstrap"


def build_plan_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    runtime: AgentRuntime | None = None,
):
    """Build the current executable graph through the new runtime facade."""

    effective_checkpointer = checkpointer or build_default_checkpointer()
    return _build_legacy_plan_graph(
        checkpointer=effective_checkpointer,
        runtime=runtime,
    )
