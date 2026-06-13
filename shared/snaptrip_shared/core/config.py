"""应用配置 —— Pydantic-Settings 统一管理。

所有配置从环境变量读取，禁止 os.getenv 散落各处。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover - fallback for lightweight test envs
    from pydantic import BaseModel

    class BaseSettings(BaseModel):  # type: ignore[no-redef]
        """Fallback settings base when pydantic-settings is unavailable."""

    def SettingsConfigDict(**kwargs):  # type: ignore[no-redef]  # noqa: N802  # pragma: no cover
        return kwargs


# 项目根目录 = shared/snaptrip_shared/core/config.py → 上 4 层
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET_KEY: str = "change-me-jwt-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    DATABASE_URL: str = (
        "postgresql+asyncpg://snaptrip:snaptrip@localhost:5432/snaptrip_dev"
    )
    DATABASE_TEST_URL: str = (
        "postgresql+asyncpg://snaptrip:snaptrip@localhost:5433/snaptrip_test"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TEST_URL: str = "redis://localhost:6380/0"
    REDIS_PASSWORD: str = ""
    REDIS_POOL_SIZE: int = 10

    SNAPTRIP_MARKETPLACE_URL: str = "http://marketplace:8000"

    # ── LLM (LiteLLM Gateway) ──
    LITELLM_BASE_URL: str = "http://litellm-proxy:4000/v1"
    LITELLM_API_KEY: str = ""
    LLM_DEFAULT_MODEL: str = "deepseek-v4-pro"
    LLM_PROVIDER_CONFIG: str = "litellm/models.toml"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.7
    LLM_ENABLE_THINKING: bool = True
    LLM_REASONING_EFFORT: str = "high"  # "high" | "max"
    LLM_STRICT_MODE: bool = False  # DeepSeek Beta, 暂不默认开启
    LLM_ADAPTER: str = "pydanticai"  # "pydanticai" | "litellm"

    AGENT_TIMEOUT: int = 300
    AGENT_MAX_RETRIES: int = 2
    AGENT_LLM_TEMPERATURE: float = 0.3

    RATE_LIMIT_IP_PER_MIN: int = 100
    RATE_LIMIT_USER_PER_MIN: int = 300

    AMAP_API_KEY: str = ""
    AMAP_BASE_URL: str = "https://restapi.amap.com"
    AMAP_TIMEOUT: int = 3
    AMAP_SSL_VERIFY: bool = True
    AMAP_GEOCODE_CACHE_TTL: int = 86400
    AMAP_POI_CACHE_TTL: int = 3600
    AMAP_QPS_LIMIT: int = 10
    AMAP_DAILY_LIMIT: int = 5000

    @property
    def effective_database_url(self) -> str:
        if self.APP_ENV == "test":
            return self.DATABASE_TEST_URL
        return self.DATABASE_URL

    @property
    def amap_enabled(self) -> bool:
        return bool(self.AMAP_API_KEY)

    COMPOSE_PROJECT_NAME: str = "snaptrip"


settings = Settings()
