"""structlog 结构化日志配置。

替换项目中的 print() 调用，统一输出 JSON 格式的结构化日志。

用法:
  from snaptrip_shared.core.logging import get_logger
  logger = get_logger(__name__)
  logger.info("event_name", key1=value1, key2=value2)

Author: SnapTrip Team
Date: 2026-05-18
"""

from __future__ import annotations

from typing import Any

from snaptrip_shared.core.config import settings

try:
    import structlog
except ModuleNotFoundError:  # pragma: no cover - fallback for lightweight test envs
    structlog = None  # type: ignore[assignment]


def setup_logging(level: str | None = None) -> None:
    log_level = (level or settings.LOG_LEVEL).upper()
    if structlog is None:
        import logging

        logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
        return

    is_json = settings.LOG_FORMAT == "json"

    renderer = structlog.processors.JSONRenderer() if is_json else structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.set_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    import logging

    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))


def get_logger(name: str | None = None) -> Any:
    if structlog is None:
        import logging

        return logging.getLogger(name or __name__)
    return structlog.get_logger(name or __name__)


setup_logging()
