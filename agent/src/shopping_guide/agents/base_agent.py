"""BaseAgent — template method pattern with retry, fallback, and timeout.

All specialist agents inherit from this base class. Subclasses implement
`_execute()`, and the base `run()` method wraps it with timing, exponential
backoff retry via tenacity, and graceful fallback.

Adapted from refer/multi-agent-ecommerce-system/python/agents/base_agent.py
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from shopping_guide.models.schemas import AgentResult

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Template method base for all agents.

    Provides:
      - run() wrapping _execute() with timing + retry + fallback
      - Exponential backoff: multiplier=0.5, min=0.5s, max=4s
      - Error rate tracking for observability
    """

    def __init__(self, name: str, timeout: float = 10.0, max_retries: int = 2):
        self.name = name
        self.timeout = timeout
        self.max_retries = max_retries
        self._call_count = 0
        self._error_count = 0

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> AgentResult:
        """Core logic — implemented by each concrete agent subclass."""

    async def run(self, **kwargs: Any) -> AgentResult:
        """Public entry point: wraps _execute with timing, retries, and fallback."""
        start = time.perf_counter()
        self._call_count += 1

        try:
            result = await self._retry_execute(**kwargs)
            result.latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "agent.success agent=%s latency_ms=%.1f",
                self.name,
                result.latency_ms,
            )
            return result
        except Exception as exc:
            self._error_count += 1
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("agent.failed agent=%s error=%s", self.name, exc)
            return self._fallback(latency_ms, exc)

    async def _retry_execute(self, **kwargs: Any) -> AgentResult:
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            reraise=True,
        )
        async def _inner():
            return await self._execute(**kwargs)

        return await _inner()

    def _fallback(self, latency_ms: float, exc: Exception) -> AgentResult:
        """Return a degraded but valid result when agent fails."""
        return AgentResult(
            agent_name=self.name,
            success=False,
            latency_ms=latency_ms,
            error=str(exc),
            confidence=0.0,
        )

    @property
    def error_rate(self) -> float:
        if self._call_count == 0:
            return 0.0
        return self._error_count / self._call_count
