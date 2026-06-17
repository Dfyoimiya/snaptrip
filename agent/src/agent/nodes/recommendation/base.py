"""BaseRecommendationAgent —— 推荐 Agent 基类。

适配自 BaseSpecialist + multi-agent-ecommerce-system 的 BaseAgent 模式。
增加:
  - timeout / max_retries 控制
  - run() 方法包装 retry + timing + fallback
  - AgentResult 标准化返回

子类只需实现 _execute(**kwargs) → AgentResult 即可获得全功能。
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """标准化 Agent 执行结果。"""

    agent_name: str
    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    confidence: float = 1.0
    error: str | None = None

    @classmethod
    def failed(cls, agent_name: str, error: str, latency_ms: float = 0.0) -> "AgentResult":
        return cls(agent_name=agent_name, success=False, error=error, latency_ms=latency_ms, confidence=0.0)


class BaseRecommendationAgent(ABC):
    """推荐 Agent 抽象基类。

    子类设置:
      - agent_name: str — Agent 标识
      - max_retries: int — 最大重试次数 (default 2)
      - timeout: float — 超时秒数 (default 10.0)

    子类实现:
      - async _execute(**kwargs) → AgentResult
    """

    agent_name: str = ""
    max_retries: int = 2
    timeout: float = 10.0

    def __init__(self) -> None:
        self._call_count = 0
        self._error_count = 0

    @property
    def error_rate(self) -> float:
        if self._call_count == 0:
            return 0.0
        return self._error_count / self._call_count

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> AgentResult:
        """子类实现核心逻辑。"""
        ...

    async def run(self, **kwargs: Any) -> AgentResult:
        """公共入口: 计时 + 重试 + 降级回退。"""
        t0 = time.perf_counter()
        self._call_count += 1

        last_exc: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                result = await asyncio.wait_for(
                    self._execute(**kwargs),
                    timeout=self.timeout,
                )
                result.latency_ms = (time.perf_counter() - t0) * 1000
                return result
            except asyncio.TimeoutError:
                last_exc = asyncio.TimeoutError(f"{self.agent_name} timeout after {self.timeout}s")
                logger.warning("%s: attempt %d/%d timed out", self.agent_name, attempt + 1, self.max_retries)
            except Exception as exc:
                last_exc = exc
                logger.warning("%s: attempt %d/%d failed: %s", self.agent_name, attempt + 1, self.max_retries, exc)

            if attempt < self.max_retries - 1:
                delay = 0.5 * (2**attempt)
                await asyncio.sleep(delay)

        self._error_count += 1
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.error("%s: all %d attempts failed", self.agent_name, self.max_retries)
        return AgentResult.failed(self.agent_name, str(last_exc), latency_ms)
