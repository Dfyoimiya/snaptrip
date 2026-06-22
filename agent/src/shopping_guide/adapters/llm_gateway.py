"""LLM Gateway — usage logger (no-op stub).

Used by LiteLLM adapter to record invocation logs.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def log_llm_usage(
    model_name: str = "",
    provider: str = "litellm",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    cost_usd: float = 0.0,
    endpoint: str = "",
) -> None:
    """Record LLM invocation usage (currently log-only, future DB write)."""
    logger.debug(
        "llm_usage model=%s provider=%s prompt=%d completion=%d latency=%d cost=%.6f",
        model_name,
        provider,
        prompt_tokens,
        completion_tokens,
        latency_ms,
        cost_usd,
    )
