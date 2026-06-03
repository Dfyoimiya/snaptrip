"""事件端口。"""

from __future__ import annotations

from typing import Protocol

from agent.schemas.events import RuntimeEvent


class EventSinkPort(Protocol):
    async def emit(self, event: RuntimeEvent) -> None: ...
