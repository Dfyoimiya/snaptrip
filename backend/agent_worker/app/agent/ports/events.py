"""Runtime event sink interfaces."""

from __future__ import annotations

from typing import Protocol

from agent_worker.app.agent.schemas.events import RuntimeEvent


class EventSinkPort(Protocol):
    """Sink used by runtime nodes to emit structured events."""

    async def emit(self, event: RuntimeEvent) -> None: ...
