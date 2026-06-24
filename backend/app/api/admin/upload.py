"""Admin 文件上传 API — 图片上传至 MinIO 对象存储。

POST /api/v1/admin/upload/image — 单图上传, 返回 URL

Author: SnapTrip Team
Date: 2026-06-24
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile
from snaptrip_shared.core.response import success

from app.core.oss import get_oss_client
from app.core.rbac import require_admin_user

router = APIRouter(prefix="/admin/upload", tags=["admin-upload"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/svg+xml",
    "application/octet-stream",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

EXT_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}


def _guess_extension(filename: str | None) -> str:
    if filename:
        dot = filename.rfind(".")
        if dot > 0:
            ext = filename[dot:].lower()
            if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"):
                return ext
    return ".jpg"


def _generate_object_name(filename: str | None) -> str:
    """Generate a unique object name under products/ prefix."""
    ext = _guess_extension(filename)
    date_prefix = datetime.utcnow().strftime("%Y/%m")
    return f"products/{date_prefix}/{uuid.uuid4().hex}{ext}"


@router.post("/image")
async def upload_image(
    file: UploadFile,
    _admin=Depends(require_admin_user),
):
    """上传单张图片到 MinIO, 返回公开 URL 和 presigned URL。

    Content-Type 仅允许 image/* 或 octet-stream, 最大 10 MB。
    """
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        return success(data=None, message=f"不支持的图片格式: {file.content_type}")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        return success(data=None, message=f"图片大小不能超过 {MAX_FILE_SIZE // (1024 * 1024)} MB")

    # 优先从文件扩展名推断 MIME, 避免 application/octet-stream 存入 MinIO
    ext = _guess_extension(file.filename)
    content_type = EXT_TO_MIME.get(ext, file.content_type or "image/jpeg")
    object_name = _generate_object_name(file.filename)

    client = get_oss_client()
    url = await client.upload(object_name, data, content_type)
    presigned = await client.get_presigned_url(object_name)

    return success(
        data={
            "url": url,
            "presigned_url": presigned,
            "object_name": object_name,
            "size": len(data),
        }
    )
