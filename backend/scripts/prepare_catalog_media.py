"""下载商品图片并生成品牌 Logo 资源。

运行:
    cd backend
    uv run python scripts/prepare_catalog_media.py
"""

from __future__ import annotations

import asyncio
import html
from pathlib import Path

import httpx
from snaptrip_shared.core.logging import get_logger

from app.data.catalog_media import BRAND_LOGO_ASSETS, PRODUCT_IMAGE_ASSETS

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ROOTS = (PROJECT_ROOT / "mall-web" / "public", PROJECT_ROOT / "frontend" / "public")
REQUEST_TIMEOUT_SECONDS = 30.0
SIMPLE_ICONS_BASE_URL = "https://cdn.simpleicons.org"


class CatalogMediaPreparationError(RuntimeError):
    """媒体资源准备失败。"""


def _wordmark_svg(brand_name: str) -> str:
    safe_name = html.escape(brand_name)
    font_size = 28 if len(brand_name) <= 10 else 20
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="120" '
        'viewBox="0 0 240 120" role="img">'
        '<rect width="240" height="120" rx="18" fill="#f8fafc"/>'
        '<rect x="5" y="5" width="230" height="110" rx="14" fill="none" '
        'stroke="#e2e8f0" stroke-width="2"/>'
        f'<text x="120" y="68" text-anchor="middle" font-size="{font_size}" '
        'font-family="Arial, PingFang SC, Microsoft YaHei, sans-serif" '
        f'font-weight="700" fill="#1e293b">{safe_name}</text>'
        "</svg>"
    )


async def _download(client: httpx.AsyncClient, url: str) -> bytes:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise CatalogMediaPreparationError(f"下载媒体资源失败: {url}") from exc
    return response.content


async def prepare_media() -> None:
    """下载媒体资源，并复制到两个前端公共目录。"""

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "SnapTrip catalog media preparation"},
    ) as client:
        product_payloads: dict[str, bytes] = {}
        for asset_key, asset in PRODUCT_IMAGE_ASSETS.items():
            product_payloads[asset.file_name] = await _download(client, str(asset.source_url))
            logger.info("catalog_product_image_downloaded", asset=asset_key)

        brand_payloads: dict[str, bytes] = {}
        for brand_name, asset in BRAND_LOGO_ASSETS.items():
            payload: bytes | None = None
            if asset.icon_slug:
                try:
                    payload = await _download(
                        client,
                        f"{SIMPLE_ICONS_BASE_URL}/{asset.icon_slug}/111827",
                    )
                except CatalogMediaPreparationError:
                    logger.info(
                        "catalog_brand_icon_fallback",
                        brand=brand_name,
                        icon_slug=asset.icon_slug,
                    )
            brand_payloads[asset.file_name] = payload or _wordmark_svg(brand_name).encode()

    for public_root in PUBLIC_ROOTS:
        product_dir = public_root / "images" / "catalog" / "products"
        brand_dir = public_root / "images" / "catalog" / "brands"
        product_dir.mkdir(parents=True, exist_ok=True)
        brand_dir.mkdir(parents=True, exist_ok=True)

        for file_name, payload in product_payloads.items():
            (product_dir / file_name).write_bytes(payload)
        for file_name, payload in brand_payloads.items():
            (brand_dir / file_name).write_bytes(payload)

        logger.info(
            "catalog_media_written",
            public_root=str(public_root),
            product_images=len(product_payloads),
            brand_logos=len(brand_payloads),
        )


if __name__ == "__main__":
    asyncio.run(prepare_media())
