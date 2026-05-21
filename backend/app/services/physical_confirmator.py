"""Physical Confirmator —— UNKNOWN 态异步确认 + 死信队列兜底。

HTTP 超时后不立即判定失败，而是:
  1. 延迟 5s 调用 provider.query_status()
  2. CONFIRMED → 更新 BookingRecord, 不触发补偿
  3. FAILED → 标记失败, 走 Fallback
  4. 仍 UNKNOWN → 指数退避重试 (5s, 10s, 20s)
  5. 最终仍 UNKNOWN → 入死信队列 (DLQ)，人工介入

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.schemas.tool_provider import PhysicalActionState

logger = logging.getLogger(__name__)

# 确认重试策略
_CONFIRM_RETRY_DELAYS = [5.0, 10.0, 20.0]  # 指数退避
_MAX_CONFIRM_ATTEMPTS = 3


# ------------------------------------------------------------------
# protocols / interfaces
# ------------------------------------------------------------------


class BookingRecordStore(Protocol):
    """BookingRecord 持久化接口（Protocol，方便测试 mock）。"""

    async def mark_physical_state(self, record_id: str, state: PhysicalActionState) -> None: ...

    async def get(self, record_id: str) -> dict[str, Any] | None: ...


class DeadLetterQueue(Protocol):
    """死信队列接口。"""

    async def enqueue(self, record_id: str, reason: str, attempts: int) -> None: ...


class ProviderStatusPort(Protocol):
    """Provider 状态查询接口。"""

    async def query_status(self, tool_name: str, booking_ref: str) -> PhysicalActionState: ...


# ------------------------------------------------------------------
# types
# ------------------------------------------------------------------


@dataclass
class ConfirmationResult:
    """确认结果"""

    record_id: str
    final_state: PhysicalActionState
    attempts: int = 0
    dlq_enqueued: bool = False


# ------------------------------------------------------------------
# confirmator
# ------------------------------------------------------------------


class PhysicalConfirmator:
    """HTTP 超时后异步确认 UNKNOWN 态的最终结果。

    用法:
      confirmator = PhysicalConfirmator(provider, store, dlq)
      result = await provider.call(...)
      if result.physical_state == PhysicalActionState.UNKNOWN:
          await confirmator.schedule_confirmation(record_id, tool_name, result.booking_ref)
    """

    def __init__(
        self,
        provider: ProviderStatusPort,
        store: BookingRecordStore,
        dlq: DeadLetterQueue | None = None,
    ) -> None:
        self._provider = provider
        self._store = store
        self._dlq = dlq

    async def schedule_confirmation(self, record_id: str, tool_name: str, booking_ref: str) -> None:
        """调度异步确认任务（不阻塞当前请求）。

        使用 asyncio.create_task 启动后台确认循环。
        """
        asyncio.create_task(self._confirm_loop(record_id, tool_name, booking_ref))
        logger.info(
            "confirmator_scheduled record_id=%s tool=%s ref=%s",
            record_id,
            tool_name,
            booking_ref,
        )

    async def confirm_sync(self, record_id: str, tool_name: str, booking_ref: str) -> ConfirmationResult:
        """同步确认（用于需要即时结果的场景）。"""
        return await self._confirm_loop(record_id, tool_name, booking_ref)

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    async def _confirm_loop(self, record_id: str, tool_name: str, booking_ref: str) -> ConfirmationResult:
        """异步确认循环。

        指数退避: 5s → 10s → 20s, 最多 3 次。
        """
        for attempt, delay in enumerate(_CONFIRM_RETRY_DELAYS):
            await asyncio.sleep(delay)

            try:
                state = await self._provider.query_status(tool_name, booking_ref)
            except Exception as e:
                logger.warning(
                    "confirmator_query_failed attempt=%d tool=%s error=%s",
                    attempt + 1,
                    tool_name,
                    e,
                )
                continue

            if state == PhysicalActionState.CONFIRMED:
                await self._store.mark_physical_state(record_id, PhysicalActionState.CONFIRMED)
                logger.info(
                    "confirmator_resolved_confirmed record_id=%s tool=%s attempts=%d",
                    record_id,
                    tool_name,
                    attempt + 1,
                )
                return ConfirmationResult(
                    record_id=record_id,
                    final_state=PhysicalActionState.CONFIRMED,
                    attempts=attempt + 1,
                )

            if state == PhysicalActionState.FAILED:
                await self._store.mark_physical_state(record_id, PhysicalActionState.FAILED)
                logger.info(
                    "confirmator_resolved_failed record_id=%s tool=%s attempts=%d",
                    record_id,
                    tool_name,
                    attempt + 1,
                )
                return ConfirmationResult(
                    record_id=record_id,
                    final_state=PhysicalActionState.FAILED,
                    attempts=attempt + 1,
                )

            logger.info(
                "confirmator_still_unknown record_id=%s tool=%s attempt=%d",
                record_id,
                tool_name,
                attempt + 1,
            )

        # 仍然 UNKNOWN → DLQ 人工介入
        logger.critical(
            "confirmator_unresolvable record_id=%s tool=%s ref=%s",
            record_id,
            tool_name,
            booking_ref,
        )
        if self._dlq:
            await self._dlq.enqueue(
                record_id,
                reason=f"unresolvable_unknown tool={tool_name} ref={booking_ref}",
                attempts=_MAX_CONFIRM_ATTEMPTS,
            )

        return ConfirmationResult(
            record_id=record_id,
            final_state=PhysicalActionState.UNKNOWN,
            attempts=_MAX_CONFIRM_ATTEMPTS,
            dlq_enqueued=self._dlq is not None,
        )
