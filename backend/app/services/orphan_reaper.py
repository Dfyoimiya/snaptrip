"""Orphan Reaper —— 孤儿预订定时清理。

FallbackEngine 替换 POI 时标记 BookingRecord → ORPHAN。
Reaper 定时扫描 ORPHAN 状态的记录，尝试 cancel。
失败 3 次后自动升级为人工工单。

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.schemas.tool_provider import PhysicalActionState

logger = logging.getLogger(__name__)

_MAX_CANCEL_RETRIES = 3


# ------------------------------------------------------------------
# protocols
# ------------------------------------------------------------------


class ToolCancelPort(Protocol):
    """工具取消接口（Protocol，方便测试 mock）。"""

    async def cancel(self, tool_name: str, booking_ref: str) -> dict: ...


class BookingRecordRepo(Protocol):
    """BookingRecord 持久化查询接口。"""

    async def find_orphans(self) -> list[dict[str, Any]]: ...

    async def mark_physical_state(self, record_id: str, state: PhysicalActionState) -> None: ...

    async def increment_retry_count(self, record_id: str, last_error: str) -> int: ...


class TicketSystem(Protocol):
    """人工工单系统接口。"""

    async def create(self, title: str, body: str, priority: str = "P1") -> None: ...


# ------------------------------------------------------------------
# reaper
# ------------------------------------------------------------------


class OrphanReaper:
    """定时扫描并清理孤儿预订。

    用法（后台定时任务）:
      reaper = OrphanReaper(adapter, repo, ticket_system)
      while True:
          await reaper.run()
          await asyncio.sleep(60)  # 每分钟扫描一次
    """

    def __init__(
        self,
        cancel_port: ToolCancelPort,
        repo: BookingRecordRepo,
        tickets: TicketSystem | None = None,
    ) -> None:
        self._cancel = cancel_port
        self._repo = repo
        self._tickets = tickets

    async def run(self) -> int:
        """扫描并清理一批孤儿预订。

        Returns:
            成功取消的数量
        """
        orphans = await self._repo.find_orphans()
        if not orphans:
            return 0

        cancelled_count = 0
        for orphan in orphans:
            success = await self._process_one(orphan)
            if success:
                cancelled_count += 1

        if orphans and cancelled_count == 0:
            logger.warning("orphan_reaper_all_failed total=%d", len(orphans))

        return cancelled_count

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    async def _process_one(self, orphan: dict[str, Any]) -> bool:
        record_id: str = orphan.get("id", "")
        tool_name: str = orphan.get("tool_name", "")
        booking_ref: str = orphan.get("booking_ref", "")
        retry_count: int = orphan.get("retry_count", 0)

        if retry_count >= _MAX_CANCEL_RETRIES:
            # 已达最大重试 → 升级工单
            await self._escalate(record_id, tool_name, booking_ref, retry_count)
            return False

        try:
            await self._cancel.cancel(tool_name, booking_ref)
            await self._repo.mark_physical_state(record_id, PhysicalActionState.CANCELLED)
            logger.info(
                "orphan_reaper_cancelled record_id=%s tool=%s ref=%s",
                record_id,
                tool_name,
                booking_ref,
            )
            return True
        except Exception as e:
            new_count = await self._repo.increment_retry_count(record_id, str(e))
            logger.warning(
                "orphan_reaper_cancel_failed record_id=%s tool=%s retry=%d error=%s",
                record_id,
                tool_name,
                new_count,
                e,
            )
            if new_count >= _MAX_CANCEL_RETRIES:
                await self._escalate(record_id, tool_name, booking_ref, new_count)
            return False

    async def _escalate(self, record_id: str, tool_name: str, booking_ref: str, retry_count: int) -> None:
        """升级为人工工单。"""
        if not self._tickets:
            logger.error(
                "orphan_reaper_no_ticket_system record_id=%s ref=%s",
                record_id,
                booking_ref,
            )
            return

        title = f"孤儿预订无法取消: {booking_ref}"
        body = f"record_id={record_id}\ntool={tool_name}\nbooking_ref={booking_ref}\nretry_count={retry_count}\n"

        try:
            await self._tickets.create(title=title, body=body, priority="P1")
            logger.info("orphan_reaper_escalated record_id=%s", record_id)
        except Exception as e:
            logger.error(
                "orphan_reaper_escalation_failed record_id=%s error=%s",
                record_id,
                e,
            )
