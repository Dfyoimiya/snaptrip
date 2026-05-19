"""In-memory runtime event store with optional persistence."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from app.ports.events import EventSinkPort
from app.ports.repositories import RuntimeEventRepositoryPort
from app.schemas.agent.events import RuntimeEvent


class RuntimeEventStore(EventSinkPort):
    """Append-only runtime event store for SSE and audit."""

    def __init__(self, repository: RuntimeEventRepositoryPort | None = None) -> None:
        self._repository = repository
        self._events: dict[str, list[RuntimeEvent]] = defaultdict(list)
        self._conditions: dict[str, asyncio.Condition] = defaultdict(asyncio.Condition)

    async def emit(self, event: RuntimeEvent) -> None:
        self._events[event.plan_id].append(event)
        condition = self._conditions[event.plan_id]
        async with condition:
            condition.notify_all()
        if self._repository is not None:
            await self._repository.append(event)

    async def list_by_plan(self, plan_id: str) -> list[RuntimeEvent]:
        if self._events.get(plan_id):
            return list(self._events[plan_id])
        if self._repository is not None:
            persisted = await self._repository.list_by_plan(plan_id)
            if persisted:
                self._events[plan_id] = list(persisted)
                return list(persisted)
        return []

    async def wait_for_events(self, plan_id: str, after_index: int, timeout_s: float = 15.0) -> list[RuntimeEvent]:
        current = self._events.get(plan_id, [])
        if len(current) > after_index:
            return current[after_index:]

        condition = self._conditions[plan_id]
        try:
            async with condition:
                await asyncio.wait_for(condition.wait(), timeout=timeout_s)
        except TimeoutError:
            return []

        current = self._events.get(plan_id, [])
        return current[after_index:]
