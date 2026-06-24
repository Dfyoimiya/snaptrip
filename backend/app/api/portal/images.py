"""Portal 图片代理 — 从 MinIO 取图并流式返回给前端。

GET /api/v1/portal/images/{object_name:path}
  → 从 MinIO 下载并流式返回图片数据。

避免前端直接依赖 Docker 内部地址 (minio:9000)。

Author: SnapTrip Team
Date: 2026-06-24
"""

from __future__ import annotations

import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from snaptrip_shared.core.logging import get_logger

from app.core.oss import get_oss_client

logger = get_logger(__name__)

router = APIRouter(prefix="/images", tags=["portal-images"])

CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}


def _guess_content_type(object_name: str) -> str:
    for ext, ct in CONTENT_TYPE_MAP.items():
        if object_name.lower().endswith(ext):
            return ct
    return "image/jpeg"


@router.get("/{object_name:path}")
async def get_image(object_name: str):
    """从 MinIO 下载对象并流式返回图片。

    使用代理而非 redirect，避免暴露 Docker 内部地址。
    """
    if not object_name or object_name == "/":
        raise HTTPException(status_code=400, detail="缺少图片标识")

    client = get_oss_client()
    data = await client.download(object_name)

    if data is None:
        raise HTTPException(status_code=404, detail="图片不存在或无法访问")

    content_type = _guess_content_type(object_name)
    return StreamingResponse(io.BytesIO(data), media_type=content_type)
