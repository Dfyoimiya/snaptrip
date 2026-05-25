"""Mock Server — B端 文件上传."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, UploadFile, File

from contracts.schemas.common import Result

router = APIRouter(prefix="/upload")


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    """Mock: return a fake URL, don't actually save."""
    filename = file.filename or "image.png"
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "png"
    url = f"https://mock-cdn.example.com/uploads/{uuid.uuid4().hex}.{ext}"
    return Result(data={"url": url, "filename": filename})
