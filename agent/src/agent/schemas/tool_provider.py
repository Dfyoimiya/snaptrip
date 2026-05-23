"""Tool Provider Schema —— 物理操作状态机、Provider 返回值、配置模型。

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ===== 物理操作状态机 =====


class PhysicalActionState(StrEnum):
    """物理操作状态机 —— 追踪 L2 工具在真实世界中的生命周期。

    状态流转:
      PENDING → CONFIRMED (正常)
      PENDING → FAILED (确认失败)
      PENDING → UNKNOWN (HTTP 超时/网络错误)
      UNKNOWN → PENDING_CONFIRMATION → CONFIRMED | FAILED | UNKNOWN
      UNKNOWN → CANCELLED (Saga 补偿)
      CONFIRMED → ORPHAN → CANCELLED (Fallback 替换 POI)
      PENDING → EXPIRED (超时未确认)

    终态: CONFIRMED, FAILED, CANCELLED, EXPIRED
    中间态: PENDING, UNKNOWN, PENDING_CONFIRMATION, ORPHAN
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    UNKNOWN = "unknown"
    PENDING_CONFIRMATION = "pending_confirmation"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    ORPHAN = "orphan"


# ===== Provider 返回值 =====


class ToolProviderResult(BaseModel):
    """Provider 调用返回值 —— 单工具原子操作结果。"""

    status: Literal["success", "failure", "degraded", "unknown"] = "success"
    data: dict[str, Any] | None = None
    booking_ref: str | None = None  # 第三方返回的预订凭证
    physical_state: PhysicalActionState = PhysicalActionState.PENDING
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0
    retryable: bool = False


# ===== 工具配置模型 =====


class ToolProviderConfig(BaseModel):
    """单个工具的完整运行时配置 —— 对应 tools.toml 中的一条。

    字段来源:
      - tools.toml: 所有字段均可从 TOML 加载
      - 代码硬编码: 当 TOML 不可用时作为后备
    """

    name: str
    provider: str = "mock"
    human_readable_name: str = ""
    llm_description: str = ""
    is_idempotent: bool = True
    physical_impact: bool = False
    timeout_ms: int = 3000
    max_retries: int = 2
    retry_delay_ms: int = 1000
    idempotency_ttl_sec: int = 3600
    circuit_breaker_threshold: int = 5
    circuit_recovery_s: int = 30
    compensation: str | None = (
        None  # 补偿策略名: "cancel_booking" | "cancel_ticket" | ...
    )


# ===== Saga 补偿 =====


class SagaStep(BaseModel):
    """Saga 事务中的单个已执行步骤 —— 用于失败时逆序补偿。"""

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tool_name: str
    booking_ref: str | None = None
    physical_impact: bool = False
    params: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    physical_state: PhysicalActionState = PhysicalActionState.PENDING
