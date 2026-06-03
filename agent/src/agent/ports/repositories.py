"""仓库端口 —— 持久化抽象。"""

from __future__ import annotations

from typing import Protocol

from agent.schemas.events import RuntimeEvent


class RuntimeEventRepositoryPort(Protocol):
    async def append(self, event: RuntimeEvent) -> None: ...
    async def list_by_plan(self, plan_id: str) -> list[RuntimeEvent]: ...
    async def get_events_after(self, plan_id: str, event_id: str) -> list[RuntimeEvent]: ...


