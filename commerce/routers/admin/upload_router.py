"""B端 文件上传路由."""

from fastapi import APIRouter, Request, UploadFile
from contracts.schemas.common import Result

router = APIRouter(prefix="/upload")


def _svc(request: Request):
    return request.app.state.commerce_services


@router.post("/image")
async def upload_image(file: UploadFile, request: Request) -> Result:
    return _svc(request).admin.upload_image(file)
