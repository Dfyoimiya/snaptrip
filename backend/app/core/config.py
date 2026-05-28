"""电商域配置 —— 扩展全局 Settings，新增 OSS / 支付 / ES / 短信等基础设施配置。

用法:
    from app.core.config import commerce_settings
    oss_endpoint = commerce_settings.OSS_ENDPOINT

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover
    from pydantic import BaseModel

    class BaseSettings(BaseModel):  # type: ignore[no-redef]
        pass

    def SettingsConfigDict(**kwargs):  # type: ignore[no-redef]  # noqa: N802
        return kwargs


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

    # ── 支付网关 (预留) ──
    PAYMENT_GATEWAY: str = "mock"
    PAYMENT_MOCK_TIMEOUT: int = 3

    # ── 物流查询 (预留) ──
    LOGISTICS_PROVIDER: str = "mock"

    # ── 短信服务 (预留) ──
    SMS_PROVIDER: str = "mock"

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
