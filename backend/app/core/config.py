"""应用配置 —— Pydantic-Settings 统一管理。

所有配置从环境变量读取，禁止 os.getenv 散落各处。

包含：
- Settings: 通用应用配置
- CommerceSettings: 电商域配置 (OSS / 支付 / ES / 短信)

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = ""
    JWT_SECRET_KEY: str = ""
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

    LLM_DEFAULT_MODEL: str = "deepseek-chat"

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

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        """Ensure secret keys are set in production; auto-generate in dev."""
        if self.APP_ENV != "development":
            if not self.APP_SECRET_KEY:
                raise ValueError(
                    "APP_SECRET_KEY must be set via environment variable in production mode"
                )
            if not self.JWT_SECRET_KEY:
                raise ValueError(
                    "JWT_SECRET_KEY must be set via environment variable in production mode"
                )
        else:
            if not self.APP_SECRET_KEY:
                object.__setattr__(self, "APP_SECRET_KEY", os.urandom(32).hex())
            if not self.JWT_SECRET_KEY:
                object.__setattr__(self, "JWT_SECRET_KEY", os.urandom(32).hex())
        return self

    COMPOSE_PROJECT_NAME: str = "snaptrip"


settings = Settings()


class CommerceSettings(BaseSettings):
    """电商基础设施配置 —— 所有值从环境变量读取，禁止硬编码。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="COMMERCE_",
    )

    # ── OSS 对象存储 (MinIO / S3 兼容) ──
    OSS_ENDPOINT: str = "localhost:9000"
    OSS_ACCESS_KEY: str = "minioadmin"
    OSS_SECRET_KEY: str = "minioadmin"
    OSS_BUCKET: str = "snaptrip-commerce"
    OSS_SECURE: bool = False
    OSS_REGION: str = "us-east-1"
    OSS_PRESIGNED_EXPIRE: int = 3600

    # ── Elasticsearch ──
    ES_HOSTS: str = "http://localhost:9200"
    ES_USERNAME: str = ""
    ES_PASSWORD: str = ""
    ES_INDEX_PRODUCTS: str = "commerce_products"
    ES_SEARCH_TIMEOUT: int = 5

    # ── 管理后台 ──
    ADMIN_DEFAULT_PASSWORD: str = "admin123"
    ADMIN_JWT_EXPIRE_HOURS: int = 24

    # ── 业务参数 ──
    ORDER_AUTO_CANCEL_MINUTES: int = 30
    ORDER_AUTO_CONFIRM_DAYS: int = 15
    COUPON_EXPIRE_DAYS: int = 7  # 优惠券默认有效期

    @property
    def es_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.ES_HOSTS.split(",") if h.strip()]


commerce_settings = CommerceSettings()
