"""OSS 对象存储适配器 —— MinIO / S3 兼容异步客户端。

用途: 商品图片、轮播图、品牌Logo上传与预签名URL生成。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from snaptrip_shared.core.logging import get_logger

from app.core.config import commerce_settings

logger = get_logger(__name__)


class OSSClientProtocol(Protocol):
    """OSS 客户端抽象接口"""

    async def upload(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """上传文件, 返回公网访问URL"""
        ...

    async def get_presigned_url(self, object_name: str, expires: int | None = None) -> str | None:
        """生成预签名下载URL"""
        ...

    async def delete(self, object_name: str) -> bool:
        """删除文件"""
        ...


class MinioOSSClient:
    """MinIO / S3 兼容 OSS 异步客户端 —— 生产环境使用"""

    def __init__(self) -> None:
        self._client = None
        self._endpoint = commerce_settings.OSS_ENDPOINT
        self._access_key = commerce_settings.OSS_ACCESS_KEY
        self._secret_key = commerce_settings.OSS_SECRET_KEY
        self._bucket = commerce_settings.OSS_BUCKET
        self._secure = commerce_settings.OSS_SECURE
        self._region = commerce_settings.OSS_REGION
        self._presigned_expire = commerce_settings.OSS_PRESIGNED_EXPIRE
        self._initialized = False

    async def _ensure_client(self):
        """懒初始化 MinIO 客户端 —— 避免导入时因缺少依赖失败"""
        if self._initialized:
            return
        try:
            from miniopy_async import Minio

            self._client = Minio(
                endpoint=self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
                region=self._region,
            )
        except ImportError:
            logger.warning("oss_minio_import_failed", fallback="mock")
            raise RuntimeError(
                "miniopy-async 未安装。安装命令: pip install miniopy-async"
            ) from None
        self._initialized = True

    async def _ensure_bucket(self) -> None:
        await self._ensure_client()
        assert self._client is not None
        try:
            exists = await self._client.bucket_exists(self._bucket)
            if not exists:
                await self._client.make_bucket(self._bucket, location=self._region)
                logger.info("oss_bucket_created", bucket=self._bucket)
        except Exception:
            logger.warning("oss_bucket_check_failed", bucket=self._bucket)

    async def upload(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        await self._ensure_bucket()
        assert self._client is not None
        import io

        await self._client.put_object(
            bucket_name=self._bucket,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        url = f"{'https' if self._secure else 'http'}://{self._endpoint}/{self._bucket}/{object_name}"
        logger.info("oss_upload_success", object_name=object_name, size=len(data))
        return url

    async def get_presigned_url(self, object_name: str, expires: int | None = None) -> str | None:
        await self._ensure_client()
        assert self._client is not None
        try:
            expire_seconds = expires or self._presigned_expire
            url = await self._client.presigned_get_object(
                bucket_name=self._bucket,
                object_name=object_name,
                expires=asyncio.timedelta(seconds=expire_seconds),
            )
            return url
        except Exception as exc:
            logger.warning("oss_presigned_failed", object_name=object_name, error=str(exc))
            return None

    async def delete(self, object_name: str) -> bool:
        await self._ensure_client()
        assert self._client is not None
        try:
            await self._client.remove_object(bucket_name=self._bucket, object_name=object_name)
            logger.info("oss_delete_success", object_name=object_name)
            return True
        except Exception as exc:
            logger.warning("oss_delete_failed", object_name=object_name, error=str(exc))
            return False


def get_oss_client() -> OSSClientProtocol:
    """工厂: 返回 MinIO 客户端"""
    return MinioOSSClient()
