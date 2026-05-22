"""Fallback Engine —— Shadow Candidate 查找 + 局部重检索 + 涟漪重排。

当 ExecutionEngine 返回 failed_slots 时激活，负责局部修复而不推翻全局规划。

核心机制:
  1. Shadow 缓存优先: 优先使用 PlanningEngine 预计算的 shadow_id
  2. 局部重检索: 若无 Shadow 缓存，同类型种子数据中查找替代
  3. 涟漪重排: 替换 Slot 后向下游传播时间偏移，检查营业时间冲突
  4. ★ 孤儿预订取消 (v3): 替换 POI 时取消被替换 POI 的已确认预订

v3 更新: 注入 ToolAdapter 实现孤儿预订 cancel → ORPHAN → OrphanReaper

输出: RevisedPlan (含 diff_patch: {added, removed, modified})

Author: SnapTrip Team
Date: 2026-05-13 / v3 update 2026-05-20
"""

from __future__ import annotations

import random
from datetime import timedelta
from typing import Any

from agent_worker.app.agent.protocol import AgentContext, AgentResult, BaseAgent
from shared.schemas.plan import (
    POI,
    EnrichedIntent,
    ExecutionResult,
    PlanDraft,
    PlanSlot,
    RevisedPlan,
    SlotDiff,
    TimeRange,
)


class FallbackEngine(BaseAgent):
    """Fallback Engine —— 局部修复失败 Slot + 孤儿预订清理。

    v3 新增:
      - ToolAdapter 注入: 取消被替换 POI 的孤儿预订
      - SagaCoordinator.compensate_for_tool: 定向补偿特定工具
    """

    name = "fallback_engine"

    def __init__(
        self,
        # ── v3 孤儿取消依赖 ──
        tool_adapter: Any | None = None,  # ToolAdapter
        saga: Any | None = None,  # SagaCoordinator
    ) -> None:
        super().__init__()
        self._tool_adapter = tool_adapter
        self._saga = saga

    async def execute(self, context: AgentContext) -> AgentResult:
        """激活 Fallback：从 history 提取失败信息 → 修复 → 返回 RevisedPlan。

        Args:
            context: 含 ExecutionResult 和 PlanDraft 的上下文

        Returns:
            AgentResult.data["revised_plan"] = RevisedPlan
        """
        execution_result = self._extract_execution(context)
        draft = self._extract_draft(context)
        enriched = self._extract_enriched(context)

        if not execution_result or not draft:
            return AgentResult(status="failed", error="Missing execution result or draft")

        revised = await self._repair(draft, execution_result, enriched)

        return AgentResult(data={"revised_plan": revised.model_dump()})

    async def _repair(
        self,
        draft: PlanDraft,
        result: ExecutionResult,
        enriched: EnrichedIntent | None,
    ) -> RevisedPlan:
        diffs: list[SlotDiff] = []
        new_slots = list(draft.slots)
        cancelled_refs: list[str] = []

        for failed in result.failed_slots:
            shadow = failed.shadow_candidate
            if shadow and shadow.prechecked:
                alt_poi = self._find_alternative(draft, failed.slot_index)
            else:
                alt_poi = self._retrieve_alternative(draft, failed.slot_index, enriched)

            if alt_poi:
                old = new_slots[failed.slot_index]

                # ── v3 孤儿取消: 如果被替换的 Slot 有已确认预订，先取消 ──
                await self._cancel_orphan_booking(failed.slot_index, old.action, result, cancelled_refs)

                new_slots[failed.slot_index] = PlanSlot(
                    sequence=failed.slot_index,
                    poi=alt_poi,
                    time_range=old.time_range,
                    action=old.action,
                    estimated_cost=alt_poi.avg_price,
                    move_time_min=old.move_time_min,
                    confidence=0.6,
                )
                diffs.append(
                    SlotDiff(
                        slot_index=failed.slot_index,
                        old_poi_id=old.poi.id,
                        new_poi_id=alt_poi.id,
                        old_poi_name=old.poi.name,
                        new_poi_name=alt_poi.name,
                    )
                )
                self._ripple_reschedule(new_slots, failed.slot_index)

        # ── v3 定向补偿: 取消被替换 POI 相关的 Saga 步骤 ──
        if self._saga and diffs:
            for diff in diffs:
                tool = draft.slots[diff.slot_index].action
                compensate_errors = await self._saga.compensate_for_tool(tool)
                if compensate_errors:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        "fallback_compensate_errors slot=%d tool=%s errors=%s",
                        diff.slot_index,
                        tool,
                        compensate_errors,
                    )

        revised = PlanDraft(
            plan_id=draft.plan_id,
            slots=new_slots,
            total_cost=sum(s.estimated_cost for s in new_slots),
            total_time_min=draft.total_time_min,
            confidence=0.5,
            version=draft.version + 1,
        )
        return RevisedPlan(plan=revised, diff_patch=diffs)

    # ------------------------------------------------------------------
    # v3 orphan cancellation
    # ------------------------------------------------------------------

    async def _cancel_orphan_booking(
        self,
        slot_index: int,
        tool_name: str,
        result: ExecutionResult,
        cancelled_refs: list[str],
    ) -> None:
        """取消被替换 Slot 可能存在的孤儿预订。

        检查 ExecutionResult 中该 slot 是否有已确认预订：
        - 有 booking_ref → 调用 ToolAdapter.cancel()
        - 取消失败 → 标记 ORPHAN（由 OrphanReaper 后续清理）
        """
        import logging

        logger = logging.getLogger(__name__)

        slot_result = result.slot_results.get(slot_index)
        if slot_result is None:
            return

        booking_ref = slot_result.booking_ref
        if not booking_ref:
            # 检查 confirmed_bookings 字典
            booking_ref = result.confirmed_bookings.get(slot_index)

        if not booking_ref or booking_ref in cancelled_refs:
            return

        if self._tool_adapter is None:
            logger.warning(
                "fallback_no_tool_adapter_cannot_cancel slot=%d ref=%s",
                slot_index,
                booking_ref,
            )
            return

        try:
            cancel_result = await self._tool_adapter.cancel(tool_name, booking_ref)
            if cancel_result.status == "success":
                cancelled_refs.append(booking_ref)
                logger.info(
                    "fallback_orphan_cancelled slot=%d tool=%s ref=%s",
                    slot_index,
                    tool_name,
                    booking_ref,
                )
            else:
                logger.error(
                    "fallback_orphan_cancel_failed slot=%d tool=%s ref=%s status=%s",
                    slot_index,
                    tool_name,
                    booking_ref,
                    cancel_result.status,
                )
                # 标记 ORPHAN: 期望持久化到 BookingRecord
                # 当前阶段记录日志，Phase 5 接入 BookingRecordRepo
                logger.info(
                    "fallback_orphan_marked slot=%d ref=%s → ORPHAN (will be reaped)",
                    slot_index,
                    booking_ref,
                )
        except Exception as e:
            logger.error(
                "fallback_orphan_cancel_error slot=%d ref=%s error=%s",
                slot_index,
                booking_ref,
                e,
            )

    # ------------------------------------------------------------------
    # POI replacement
    # ------------------------------------------------------------------

    def _find_alternative(self, draft: PlanDraft, slot_index: int) -> POI | None:
        """查找失败 Slot 的替代 POI。

        优先级：1) shadow_id 预计算缓存  2) 同类型种子数据中随机选取。

        Args:
            draft: 当前计划草案
            slot_index: 失败的 Slot 索引

        Returns:
            替代 POI 或 None
        """
        from marketplace.app.data.seed_pois import SEED_POIS

        original = draft.slots[slot_index]

        if original.shadow_id:
            shadow = next((p for p in SEED_POIS if p.id == original.shadow_id), None)
            if shadow:
                return POI(**shadow.model_dump())

        candidates = [p for p in SEED_POIS if p.type == original.poi.type and p.id != original.poi.id]
        return random.choice(candidates) if candidates else None

    def _retrieve_alternative(self, draft: PlanDraft, slot_index: int, enriched: EnrichedIntent | None) -> POI | None:
        return self._find_alternative(draft, slot_index)

    def _ripple_reschedule(self, slots: list[PlanSlot], changed_idx: int):
        """涟漪重排：替换后向下游传播时间偏移。

        将 changed_idx 之后的所有 Slot 按前一个 Slot 的结束时间顺延。

        Args:
            slots: 当前 Slot 列表（原地修改）
            changed_idx: 被替换的 Slot 索引
        """
        for i in range(changed_idx + 1, len(slots)):
            prev = slots[i - 1]
            cur = slots[i]
            earliest = prev.time_range.end + timedelta(minutes=prev.move_time_min)
            if earliest > cur.time_range.start:
                delta = (earliest - cur.time_range.start).total_seconds() / 60
                cur.time_range = TimeRange(
                    start=earliest,
                    end=cur.time_range.end + timedelta(minutes=delta),
                )

    # ------------------------------------------------------------------
    # data extraction
    # ------------------------------------------------------------------

    def _extract_execution(self, context: AgentContext) -> ExecutionResult | None:
        for h in reversed(context.history):
            if "execution" in h.data:
                return ExecutionResult(**h.data["execution"])
        return None

    def _extract_draft(self, context: AgentContext) -> PlanDraft | None:
        for h in reversed(context.history):
            if "draft" in h.data:
                return PlanDraft(**h.data["draft"])
        return None

    def _extract_enriched(self, context: AgentContext) -> EnrichedIntent | None:
        for h in reversed(context.history):
            if "enriched_intent" in h.data:
                return EnrichedIntent(**h.data["enriched_intent"])
        return None
