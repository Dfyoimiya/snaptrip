"""Lightweight node execution tracing decorator.

Inspired by smart-cs-multi-agent @trace_agent_call pattern.
Logs each node's latency, success/failure status, and result phase.
No OpenTelemetry dependency — uses standard logging.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Callable, cast

logger = logging.getLogger("agent.trace")


def trace_node(node_name: str) -> Callable:
    """Decorator that traces node execution with latency and status.

    Usage:
        @trace_node("admin_analyst")
        async def admin_analyst_node(state) -> dict: ...

    Log format:
        node_trace name=admin_analyst elapsed_ms=1234.5 success=true status=done
        node_trace name=admin_analyst elapsed_ms=567.8 success=false error=...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(state: dict) -> dict:
            t0 = time.monotonic()
            try:
                result = await func(state)
                elapsed_ms = (time.monotonic() - t0) * 1000
                logger.info(
                    "node_trace name=%s elapsed_ms=%.1f success=true status=%s",
                    node_name,
                    elapsed_ms,
                    result.get("status", "?"),
                )
                return cast(dict, result)
            except Exception as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                logger.error(
                    "node_trace name=%s elapsed_ms=%.1f success=false error=%s",
                    node_name,
                    elapsed_ms,
                    str(exc),
                )
                raise

        return wrapper

    return decorator
