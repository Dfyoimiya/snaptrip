"""指标收集器 —— Agent 调用指标 + 业务事件追踪。

参考 multi-agent-ecommerce-system 的 MetricsCollector 模式。

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMetric:
    """单个 Agent 的累积指标。"""
    call_count: int = 0
    success_count: int = 0
    total_latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.success_count / self.call_count if self.call_count > 0 else 1.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.call_count if self.call_count > 0 else 0.0


class MetricsCollector:
    """指标收集器 —— 内存中, 供 /metrics 端点查询。"""

    def __init__(self) -> None:
        self._agent_metrics: dict[str, AgentMetric] = defaultdict(AgentMetric)
        self._business_events: list[dict[str, Any]] = []
        self._start_time = time.time()

    # ── Agent 指标 ──

    def record_agent_call(
        self, agent_name: str, success: bool,
        latency_ms: float = 0.0, error: str = "",
    ) -> None:
        metric = self._agent_metrics[agent_name]
        metric.call_count += 1
        if success:
            metric.success_count += 1
        else:
            metric.errors.append(error[:200])
        metric.total_latency_ms += latency_ms

    def get_agent_stats(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "call_count": m.call_count,
                "success_rate": round(m.success_rate, 4),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "recent_errors": m.errors[-5:],
            }
            for name, m in self._agent_metrics.items()
        }

    # ── 业务事件 ──

    def record_business_event(self, event_type: str, **kwargs: Any) -> None:
        self._business_events.append({
            "event_type": event_type,
            "ts": time.time(),
            **kwargs,
        })
        # 保留最近 10000 条
        if len(self._business_events) > 10000:
            self._business_events = self._business_events[-5000:]

    def get_business_stats(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for ev in self._business_events:
            counts[ev["event_type"]] += 1
        return dict(counts)

    # ── 全局状态 ──

    def uptime_seconds(self) -> float:
        return time.time() - self._start_time
