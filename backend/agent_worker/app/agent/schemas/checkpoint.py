"""Checkpoint Schema —— Slot 粒度检查点。

以 Slot 为最小粒度的乐观检查点系统，确保 Incremental Replanning 时
有明确的「已冻结」与「可变更」边界。

结构:
- LockedSlot: 已确认 Slot，含 confirmed_by 列表和 booking_id
- TentativeSlot: 当前版本的草案 Slot，可在增量重规划中被替换
- ShadowSlot: 预计算的替代候选，prechecked 标记是否已预查可用性

写入策略: 用户确认→Redis+PostgreSQL / Fallback完成→Redis+PostgreSQL
读取策略: 增量重规划时，locked_slots 作为前缀固定值，仅替换 tentative 中目标 Slot

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LockedSlot(BaseModel):
    slot_index: int
    confirmed_by: list[str] = Field(default_factory=list)
    confirmed_at: datetime | None = None
    booking_id: str | None = None


class TentativeSlot(BaseModel):
    slot_index: int
    poi_id: str
    start_time: datetime
    end_time: datetime
    action: str


class ShadowSlot(BaseModel):
    slot_index: int
    alternative_poi_id: str
    prechecked: bool = False


class Checkpoint(BaseModel):
    plan_id: str
    version: int = 1
    state: str = "idle"
    locked_slots: list[LockedSlot] = Field(default_factory=list)
    tentative_slots: list[TentativeSlot] = Field(default_factory=list)
    shadow_candidates: list[ShadowSlot] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
