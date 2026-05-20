"""LLM 使用量日志记录 —— 轻量持久化层。

Provider 层负责 HTTP 通信，本模块仅负责将调用统计写入 llm_usage_logs 表。

Author: SnapTrip Team
Date: 2026-05-17 / Refactored 2026-05-20
"""

from __future__ import annotations

import logging

from app.db.session import AsyncSessionLocal
from app.models.llm_usage_log import LLMUsageLog

logger = logging.getLogger(__name__)


async def log_llm_usage(
    *,
    model_name: str,
    provider: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    cost_usd: float = 0.0,
    endpoint: str = "chat",
) -> None:
    """异步写入 llm_usage_logs 表（失败时静默忽略）。"""
    try:
        async with AsyncSessionLocal() as db:
            log = LLMUsageLog(
                model_name=model_name,
                provider=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                endpoint=endpoint,
            )
            db.add(log)
            await db.commit()
    except Exception:
        logger.warning("llm_usage_log_failed", exc_info=True)
