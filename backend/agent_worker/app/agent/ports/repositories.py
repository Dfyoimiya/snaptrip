"""Repository boundary interfaces used by the runtime."""

from __future__ import annotations

from typing import Protocol

from agent_worker.app.agent.schemas.events import RuntimeEvent
from agent_worker.app.agent.schemas.state import CheckpointSnapshot


class UserProfileRepositoryPort(Protocol):
    """Read user profile data for context loading."""

    async def get_profile(self, user_id: str) -> dict | None: ...


class PlanRepositoryPort(Protocol):
    """Read plan history for memory aggregation."""

    async def get_user_history(self, user_id: str) -> dict[str, list[str]] | None: ...


class CheckpointRepositoryPort(Protocol):
    """Persist and retrieve runtime checkpoints."""

    async def save(self, checkpoint: CheckpointSnapshot) -> None: ...

    async def load_latest(self, plan_id: str) -> CheckpointSnapshot | None: ...


class RuntimeEventRepositoryPort(Protocol):
    """Append-only event store for runtime lifecycle events."""

    async def append(self, event: RuntimeEvent) -> None: ...

    async def list_by_plan(self, plan_id: str) -> list[RuntimeEvent]: ...

    async def get_events_after(self, plan_id: str, after_timestamp: str) -> list[RuntimeEvent]: ...
