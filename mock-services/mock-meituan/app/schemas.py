"""Mock Server 统一响应模型。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    status: str = "success"
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0
