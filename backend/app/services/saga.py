"""Saga 协调器 —— 长事务补偿机制。

在 DAG 执行过程中记录已完成的物理操作步骤。当任一节点失败时，
按逆序执行补偿（cancel_booking / cancel_ticket / cancel_order）。

v3 更新: 接入 ToolAdapter 实现真实补偿调用，使用 SagaStep 结构化记录。

Author: SnapTrip Team
Date: 2026-05-17 / v3 update 2026-05-20
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol

from app.schemas.tool_provider import PhysicalActionState, SagaStep, ToolProviderResult

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# protocols
# ------------------------------------------------------------------


class ToolCancelPort(Protocol):
    """工具取消接口（避免循环导入）。"""

    async def cancel(self, tool_name: str, booking_ref: str) -> ToolProviderResult: ...


# ------------------------------------------------------------------
# coordinator
# ------------------------------------------------------------------


class SagaCoordinator:
    """Saga 协调器 —— 记录已完成步骤 + 失败时逆序补偿。

    用法:
      saga = SagaCoordinator(tool_adapter)

      # 执行工具调用前记录
      step = SagaStep(tool_name="book_table", booking_ref="bk_123", physical_impact=True)
      saga.record_step(step)

      # 如果有步骤失败，执行补偿
      errors = await saga.compensate()
      if errors:
          logger.error("compensation_errors", errors=errors)
    """

    def __init__(self, cancel_port: ToolCancelPort | None = None) -> None:
        self.transaction_id: str = str(uuid.uuid4())
        self._completed: list[SagaStep] = []
        self._cancel = cancel_port

    # ------------------------------------------------------------------
    # recording
    # ------------------------------------------------------------------

    def record_step(self, step: SagaStep) -> None:
        """记录已完成的步骤。仅物理操作需要记录（用于补偿）。"""
        if step.physical_impact:
            self._completed.append(step)
            logger.info(
                "saga_recorded transaction=%s tool=%s ref=%s",
                self.transaction_id,
                step.tool_name,
                step.booking_ref,
            )

    @property
    def completed_steps(self) -> list[SagaStep]:
        return list(self._completed)

    @property
    def has_physical_steps(self) -> bool:
        return any(s.physical_impact for s in self._completed)

    # ------------------------------------------------------------------
    # compensation
    # ------------------------------------------------------------------

    async def compensate(self) -> list[str]:
        """按逆序执行补偿。

        逆序原因: 先取消订单(order) → 再取消门票(ticket) → 最后取消桌位(table)。
        每一步补偿失败继续执行剩余补偿（best-effort），不因单步失败而中止。

        Returns:
            失败的补偿步骤列表（工具名:错误信息），空列表表示全部成功
        """
        errors: list[str] = []

        if not self._completed:
            return errors

        logger.info(
            "saga_compensate_start transaction=%s steps=%d",
            self.transaction_id,
            len(self._completed),
        )

        for step in reversed(self._completed):
            if not step.booking_ref:
                continue

            try:
                if self._cancel:
                    result = await self._cancel.cancel(step.tool_name, step.booking_ref)
                    if result.status != "success":
                        errors.append(f"{step.tool_name}/{step.booking_ref}: cancel returned {result.status}")
                    else:
                        step.physical_state = PhysicalActionState.CANCELLED
                else:
                    logger.warning("saga_no_cancel_port tool=%s ref=%s", step.tool_name, step.booking_ref)
            except Exception as e:
                error_msg = f"{step.tool_name}/{step.booking_ref}: {e}"
                errors.append(error_msg)
                logger.error("saga_compensate_failed step=%s", error_msg)

        if errors:
            logger.error(
                "saga_compensate_completed transaction=%s errors=%d total=%d",
                self.transaction_id,
                len(errors),
                len(self._completed),
            )
        else:
            logger.info(
                "saga_compensate_success transaction=%s steps=%d",
                self.transaction_id,
                len(self._completed),
            )

        self._completed.clear()
        return errors

    async def compensate_for_tool(self, tool_name: str) -> list[str]:
        """仅补偿指定工具的已完成步骤。

        FallbackEngine 替换 POI 时使用，只取消被替换 POI 的预订。
        """
        target = [s for s in self._completed if s.tool_name == tool_name]
        if not target:
            return []

        errors: list[str] = []
        for step in reversed(target):
            if not step.booking_ref or not self._cancel:
                continue
            try:
                await self._cancel.cancel(step.tool_name, step.booking_ref)
                step.physical_state = PhysicalActionState.CANCELLED
                self._completed.remove(step)
            except Exception as e:
                errors.append(f"{step.tool_name}/{step.booking_ref}: {e}")

        return errors
