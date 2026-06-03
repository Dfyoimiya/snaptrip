"""SagaCoordinator — multi-tool transactional execution.

Implements a 3-phase saga:
  Phase 1: RESERVE — execute all tools with reserve_only=True (soft state)
  Phase 2: CONFIRM — execute all tools with reserve_only=False (hard state)
  Phase 3: ROLLBACK — compensate all confirmed tools in LIFO order on any failure

Uses ToolHarness for tool execution (injected, not imported).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from agent.tools.transaction.compensation import CompensationRegistry
from agent.tools.transaction.context import TransactionContext, TxStatus

if TYPE_CHECKING:
    from agent.tools.harness.harness import ToolHarness

logger = logging.getLogger(__name__)

# Purely descriptive — SagaCoordinator doesn't hold a harness reference at init.
# The caller injects it via execute().


@dataclass
class SagaCoordinator:
    """Multi-tool saga coordinator.

    Usage:
        coordinator = SagaCoordinator()
        result = await coordinator.execute(harness, session_ctx, steps)
    """

    def __post_init__(self) -> None:
        self._comp_registry: CompensationRegistry | None = None

    async def execute(
        self,
        harness: "ToolHarness",
        session_ctx: Any,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Execute a list of tool-call steps as a saga.

        Each step is a dict: {"tool_name": str, "args": dict}.

        Returns:
            {"status": "done"|"failed", "results": [...], "rollback_failures": [...]}
        """
        tx_ctx = TransactionContext.new(session_id=session_ctx.session_id)
        self._comp_registry = CompensationRegistry()
        session_ctx.active_tx = tx_ctx

        reserved: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []

        # Phase 1: RESERVE
        for i, step in enumerate(steps):
            tool_name = step["tool_name"]
            args = {**step.get("args", {}), "reserve_only": True}

            result = await harness.execute(
                tool_name=tool_name,
                args=args,
                session_ctx=session_ctx,
                tx_ctx=tx_ctx,
            )
            results.append(result)
            if result.success:
                reserved.append({
                    "seq": i,
                    "tool_name": tool_name,
                    "args": step.get("args", {}),
                    "reserve_result": result,
                })
            else:
                logger.warning("Saga reserve failed for %s: %s", tool_name, result.data)
                # Rollback whatever was reserved
                rollback_failures = await self._comp_registry.rollback_all()
                tx_ctx.status = TxStatus.ROLLED_BACK
                return {
                    "status": "failed",
                    "phase": "reserve",
                    "results": results,
                    "rollback_failures": rollback_failures,
                }

        # Phase 2: CONFIRM
        confirmed: list[dict[str, Any]] = []
        for item in reserved:
            tool_name = item["tool_name"]
            args = {**item["args"], "reserve_only": False}

            result = await harness.execute(
                tool_name=tool_name,
                args=args,
                session_ctx=session_ctx,
                tx_ctx=tx_ctx,
            )
            results.append(result)
            if result.success:
                confirmed.append(item)
            else:
                logger.warning("Saga confirm failed for %s: %s", tool_name, result.data)
                # Phase 3: ROLLBACK
                rollback_failures = await self._comp_registry.rollback_all()
                tx_ctx.status = TxStatus.ROLLED_BACK
                return {
                    "status": "failed",
                    "phase": "confirm",
                    "results": results,
                    "rollback_failures": rollback_failures,
                }

        tx_ctx.status = TxStatus.COMMITTED
        return {
            "status": "done",
            "tx_id": tx_ctx.tx_id,
            "results": results,
            "rollback_failures": [],
        }
