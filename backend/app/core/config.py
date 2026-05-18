"""应用配置 —— Pydantic-Settings 统一管理。

所有配置从环境变量读取，禁止 os.getenv 散落各处。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET_KEY: str = "change-me-jwt-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    DATABASE_URL: str = "postgresql+asyncpg://snaptrip:snaptrip@localhost:5432/snaptrip_dev"
    DATABASE_TEST_URL: str = "postgresql+asyncpg://snaptrip:snaptrip@localhost:5433/snaptrip_test"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    MOCK_API_BASE_URL: str = "http://localhost:8001"
    MOCK_API_TIMEOUT: int = 3

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "deepseek/deepseek-v4-pro"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.7

    AGENT_TIMEOUT: int = 300
    AGENT_MAX_RETRIES: int = 2
    AGENT_LLM_TEMPERATURE: float = 0.3

    RATE_LIMIT_IP_PER_MIN: int = 100
    RATE_LIMIT_USER_PER_MIN: int = 300

    @property
    def effective_database_url(self) -> str:
        if self.APP_ENV == "test":
            return self.DATABASE_TEST_URL
        return self.DATABASE_URL

    COMPOSE_PROJECT_NAME: str = "snaptrip"


settings = Settings()
