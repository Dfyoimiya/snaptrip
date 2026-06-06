"""CompensationRegistry — LIFO rollback stack.

Every successful tool call registers a CompensationAction.
On rollback, actions execute in strict reverse-registration (LIFO) order.
Each action is retried up to max_retries before being logged as permanently failed.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class CompensationAction:
    """An idempotent compensation to undo one tool call.

    Rules:
      - action_id must be globally unique within the transaction.
      - execute must be idempotent (safe to call multiple times).
      - max_retries controls retry count after initial failure.
    """

    action_id: str
    tool_name: str
    description: str
    execute: Callable[[], Awaitable[None]]
    max_retries: int = 3

    def __hash__(self) -> int:
        return hash(self.action_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CompensationAction):
            return self.action_id == other.action_id
        return False


@dataclass
class CompensationRegistry:
    """LIFO stack of CompensationAction for a single TransactionContext.

    Guarantees:
      - Actions are registered in forward call order.
      - Rollback executes in strict reverse (LIFO) order.
      - Each action is retried up to max_retries before being logged as
        permanently failed (best-effort; does not abort remaining compensations).
      - action_id deduplication: registering the same action_id twice is a no-op.
    """

    _actions: list[CompensationAction] = field(default_factory=list)
    _executed_ids: set[str] = field(default_factory=set)

    def register(self, action: CompensationAction) -> None:
        """Register a compensation action. Duplicate action_ids are ignored."""
        if action.action_id in self._executed_ids:
            return
        existing_ids = {a.action_id for a in self._actions}
        if action.action_id not in existing_ids:
            self._actions.append(action)

    async def rollback_all(self) -> list[str]:
        """Execute all compensations in LIFO order.

        Returns:
            List of action_ids that permanently failed (after all retries).
        """
        failed: list[str] = []

        for action in reversed(self._actions):
            if action.action_id in self._executed_ids:
                continue

            success = await self._execute_with_retry(action)
            if success:
                self._executed_ids.add(action.action_id)
                logger.info(
                    "Compensated: %s (%s)", action.action_id, action.description,
                )
            else:
                failed.append(action.action_id)
                logger.error(
                    "Compensation permanently failed: %s — MANUAL INTERVENTION REQUIRED",
                    action.action_id,
                )

        return failed

    @staticmethod
    async def _execute_with_retry(action: CompensationAction) -> bool:
        for attempt in range(action.max_retries):
            try:
                await action.execute()
                return True
            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(
                    "Compensation %s attempt %d/%d failed: %s; retrying in %ds",
                    action.action_id, attempt + 1, action.max_retries, exc, wait,
                )
                await asyncio.sleep(wait)
        return False
