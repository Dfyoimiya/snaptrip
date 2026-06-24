"""将项目素材目录幂等导入商城商品目录。

默认只扫描并输出报告，不修改数据库：
    cd backend
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/import_material_catalog.py

确认后执行导入：
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/import_material_catalog.py --commit
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import re
import shutil
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

from sqlalchemy import select

from app.schemas.material_catalog import (
    MaterialCatalogDefaults,
    MaterialImportResult,
    MaterialProductDraft,
    MaterialScanReport,
)
from snaptrip_shared.core.logging import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "素材"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "backend" / "app" / "data" / "material_catalog_defaults.json"
PUBLIC_ROOTS = (PROJECT_ROOT / "mall-web" / "public", PROJECT_ROOT / "frontend" / "public")
PUBLIC_PREFIX = Path("images") / "material-catalog"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MARKET_SUFFIX_RE = re.compile(r"【行情\s*报价\s*价格\s*评测】\s*-\s*京东$")
BRACKET_RE = re.compile(r"[（(]([A-Za-z][A-Za-z0-9&+.\- ]{0,30})[）)]")
LEADING_BRAND_RE = re.compile(r"^([A-Za-z][A-Za-z0-9&+.\-]{1,30}|[\u4e00-\u9fff]{2,8})")


def load_defaults(path: Path) -> MaterialCatalogDefaults:
    """读取并验证 seed 配置。"""

    return MaterialCatalogDefaults.model_validate_json(path.read_text(encoding="utf-8"))


def natural_key(path: Path) -> tuple[object, ...]:
    """按文件名中的数字做自然排序。"""

    return tuple(int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name))


def clean_product_name(source_name: str) -> str:
    """移除采集页面后缀并压缩空白。"""

    cleaned = MARKET_SUFFIX_RE.sub("", source_name)
    cleaned = cleaned.replace("_", " ")
    return re.sub(r"\s+", " ", cleaned).strip()[:200]


def infer_brand(name: str, defaults: MaterialCatalogDefaults) -> str:
    """从商品标题推断品牌，英文括号别名优先。"""

    bracket_match = BRACKET_RE.search(name)
    if bracket_match:
        candidate = bracket_match.group(1).strip()
        return defaults.brand_aliases.get(candidate, candidate)[:64]

    leading_match = LEADING_BRAND_RE.match(name)
    if not leading_match:
        return defaults.generic_brand
    candidate = leading_match.group(1).strip()
    return defaults.brand_aliases.get(candidate, candidate)[:64]


def stable_product_sn(category: str, source_name: str) -> str:
    """根据素材路径生成稳定货号，保证重复执行时更新同一商品。"""

    digest = hashlib.sha256(f"{category}/{source_name}".encode()).hexdigest()[:16].upper()
    return f"MAT-{digest}"


def deterministic_price(category: str, source_name: str, defaults: MaterialCatalogDefaults) -> Decimal:
    """在分类价格区间内生成稳定演示价。"""

    category_defaults = defaults.categories[category]
    value = int(hashlib.sha256(source_name.encode()).hexdigest()[:12], 16) / float(0xFFFFFFFFFFFF)
    price = category_defaults.min_price + (
        category_defaults.max_price - category_defaults.min_price
    ) * Decimal(str(value))
    return price.quantize(Decimal("0.10"), rounding=ROUND_HALF_UP)


def build_summary(category: str, name: str, text_path: Path | None) -> str:
    """优先读取素材说明，否则根据标题生成不冒充官方参数的原创摘要。"""

    if text_path and text_path.exists():
        content = re.sub(r"\s+", " ", text_path.read_text(encoding="utf-8")).strip()
        if content:
            return content[:500]
    short_name = name[:100]
    return (
        f"{short_name}，归属于{category}分类。商品规格与卖点依据素材标题整理，"
        "实际颜色、尺寸、配置及包装内容请以下单页面和实物为准。"
    )


def image_files(directory: Path) -> list[Path]:
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES),
        key=natural_key,
    )


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_materials(source_root: Path, defaults: MaterialCatalogDefaults) -> MaterialScanReport:
    """扫描详情目录，并通过文件摘要匹配主图池中的同源图片。"""

    detail_root = source_root / "详情"
    main_root = source_root / "主图池"
    if not detail_root.is_dir() or not main_root.is_dir():
        raise FileNotFoundError(f"素材目录必须同时包含“详情”和“主图池”: {source_root}")

    main_by_digest: dict[str, list[Path]] = {}
    all_main_images: list[Path] = []
    for main_image in main_root.glob("*/*"):
        if main_image.is_file() and main_image.suffix.lower() in IMAGE_SUFFIXES:
            all_main_images.append(main_image)
            main_by_digest.setdefault(file_digest(main_image), []).append(main_image)

    products: list[MaterialProductDraft] = []
    matched_paths: set[Path] = set()
    detail_image_count = 0
    for category_dir in sorted((path for path in detail_root.iterdir() if path.is_dir()), key=natural_key):
        if category_dir.name not in defaults.categories:
            raise ValueError(f"seed 配置缺少分类默认值: {category_dir.name}")
        category_defaults = defaults.categories[category_dir.name]
        for product_dir in sorted((path for path in category_dir.iterdir() if path.is_dir()), key=natural_key):
            details = image_files(product_dir)
            if not details:
                logger.warning("material_product_without_images", path=str(product_dir))
                continue
            detail_image_count += len(details)
            matched: list[Path] = []
            for detail_image in details:
                for main_image in main_by_digest.get(file_digest(detail_image), []):
                    if main_image not in matched_paths:
                        matched.append(main_image)
                        matched_paths.add(main_image)

            name = clean_product_name(product_dir.name)
            text_path = product_dir / "详情.txt"
            price = deterministic_price(category_dir.name, product_dir.name, defaults)
            products.append(
                MaterialProductDraft(
                    category=category_dir.name,
                    name=name,
                    source_name=product_dir.name,
                    brand=infer_brand(name, defaults),
                    product_sn=stable_product_sn(category_dir.name, product_dir.name),
                    price=price,
                    original_price=(price * Decimal("1.15")).quantize(Decimal("0.10")),
                    stock=category_defaults.stock,
                    low_stock=category_defaults.low_stock,
                    unit=category_defaults.unit,
                    summary=build_summary(category_dir.name, name, text_path if text_path.exists() else None),
                    keywords=",".join(dict.fromkeys([category_dir.name, infer_brand(name, defaults), name[:80]]))[:255],
                    detail_images=details,
                    matched_main_images=matched,
                )
            )

    return MaterialScanReport(
        products=products,
        category_count=len({product.category for product in products}),
        detail_image_count=detail_image_count,
        main_image_count=len(all_main_images),
        matched_main_image_count=len(matched_paths),
        unmatched_main_images=sorted(set(all_main_images) - matched_paths, key=natural_key),
    )


def asset_directory(product: MaterialProductDraft) -> Path:
    category_hash = hashlib.sha1(product.category.encode()).hexdigest()[:8]
    product_hash = product.product_sn.removeprefix("MAT-").lower()
    return PUBLIC_PREFIX / category_hash / product_hash


def copy_product_assets(product: MaterialProductDraft) -> tuple[list[str], list[str], int]:
    """复制商品图片到 B/C 两端 public 目录，返回主图、详情图 URL。"""

    relative_dir = asset_directory(product)
    sources: list[Path] = []
    digest_sources: dict[str, Path] = {}
    source_digests: dict[Path, str] = {}
    for source in [*product.matched_main_images, *product.detail_images]:
        digest = file_digest(source)
        source_digests[source] = digest
        if digest not in digest_sources:
            digest_sources[digest] = source
            sources.append(source)

    digest_urls: dict[str, str] = {}
    copied = 0
    for index, source in enumerate(sources, start=1):
        filename = f"{index:02d}{source.suffix.lower()}"
        relative_path = relative_dir / filename
        digest_urls[source_digests[source]] = f"/{relative_path.as_posix()}"
        for public_root in PUBLIC_ROOTS:
            destination = public_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() or file_digest(destination) != file_digest(source):
                shutil.copy2(source, destination)
                copied += 1

    album_urls = [digest_urls[source_digests[path]] for path in sources]
    detail_urls = list(
        dict.fromkeys(digest_urls[source_digests[path]] for path in product.detail_images)
    )
    return album_urls, detail_urls, copied


def build_detail_html(product: MaterialProductDraft, detail_urls: Iterable[str]) -> str:
    """生成 C 端可直接渲染的商品富文本详情。"""

    images = "".join(
        f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(product.name, quote=True)}" '
        'loading="lazy" style="display:block;width:100%;height:auto;" />'
        for url in detail_urls
    )
    return (
        '<section class="material-product-detail">'
        f"<h2>{html.escape(product.name)}</h2>"
        f"<p>{html.escape(product.summary)}</p>"
        f"{images}</section>"
    )


def join_urls_with_limit(urls: Iterable[str], limit: int = 1000) -> str:
    """按完整 URL 拼接，避免数据库长度限制导致图片地址被截断。"""

    joined: list[str] = []
    length = 0
    for url in urls:
        next_length = length + len(url) + (1 if joined else 0)
        if next_length > limit:
            break
        joined.append(url)
        length = next_length
    return ",".join(joined)


async def import_catalog(
    report: MaterialScanReport,
    defaults: MaterialCatalogDefaults,
    publish: bool,
) -> MaterialImportResult:
    """幂等写入分类、品牌、商品与默认 SKU。"""

    from app.models.product.brand import PmsBrand
    from app.models.product.category import PmsCategory
    from app.models.product.product import PmsProduct
    from app.models.product.sku import PmsSku
    from app.services.product_service import sync_product_to_es
    from snaptrip_shared.db.session import AsyncSessionLocal

    result = MaterialImportResult()
    async with AsyncSessionLocal() as session:
        category_names = {product.category for product in report.products}
        category_rows = (
            await session.execute(
                select(PmsCategory).where(PmsCategory.level == 0, PmsCategory.name.in_(category_names))
            )
        ).scalars()
        categories = {row.name: row for row in category_rows}
        for sort, name in enumerate(sorted(category_names), start=100):
            if name in categories:
                continue
            category = PmsCategory(
                name=name,
                type="PRODUCT",
                level=0,
                sort=sort,
                nav_status=1,
                show_status=1,
                keywords=name,
                description=f"{name}素材导入分类",
            )
            session.add(category)
            await session.flush()
            categories[name] = category
            result.created_categories += 1

        brand_names = {product.brand for product in report.products}
        brand_rows = (
            await session.execute(select(PmsBrand).where(PmsBrand.name.in_(brand_names)))
        ).scalars()
        brands = {row.name: row for row in brand_rows}
        for sort, name in enumerate(sorted(brand_names), start=500):
            if name in brands:
                continue
            brand = PmsBrand(
                name=name,
                first_letter=name[:1].upper(),
                sort=sort,
                factory_status=1,
                show_status=1,
                brand_story=f"{name}品牌商品由项目素材目录导入。",
            )
            session.add(brand)
            await session.flush()
            brands[name] = brand
            result.created_brands += 1

        product_sns = [product.product_sn for product in report.products]
        product_rows = (
            await session.execute(select(PmsProduct).where(PmsProduct.product_sn.in_(product_sns)))
        ).scalars()
        existing_products = {row.product_sn: row for row in product_rows if row.product_sn}

        for draft in report.products:
            album_urls, detail_urls, copied = copy_product_assets(draft)
            result.copied_assets += copied
            product = existing_products.get(draft.product_sn)
            if product is None:
                product = PmsProduct(name=draft.name, product_sn=draft.product_sn, price=draft.price)
                session.add(product)
                result.created_products += 1
            else:
                result.updated_products += 1

            product.name = draft.name
            product.sub_title = draft.summary[:255]
            product.brand_id = brands[draft.brand].id
            product.category_id = categories[draft.category].id
            product.price = draft.price
            product.original_price = draft.original_price
            product.stock = draft.stock
            product.default_pic = album_urls[0]
            product.pics = join_urls_with_limit(album_urls)
            product.album_pics = join_urls_with_limit(album_urls[1:])
            product.description = build_detail_html(draft, detail_urls)
            product.keywords = draft.keywords
            product.unit = draft.unit
            product.service_ids = ",".join(defaults.services)
            product.publish_status = int(publish)
            product.verify_status = int(publish)
            product.new_status = 1
            product.recommend_status = 0
            product.is_deleted = False
            product.deleted_at = None
            await session.flush()

            sku_code = f"{draft.product_sn}-DEFAULT"
            sku = (
                await session.execute(
                    select(PmsSku).where(PmsSku.product_id == product.id, PmsSku.sku_code == sku_code)
                )
            ).scalar_one_or_none()
            if sku is None:
                sku = PmsSku(product_id=product.id, sku_code=sku_code, spec='{"规格":"默认"}')
                session.add(sku)
            sku.price = draft.price
            sku.stock = draft.stock
            sku.low_stock = draft.low_stock
            sku.pic = album_urls[0]
            await session.flush()

            if publish:
                try:
                    await sync_product_to_es(session, product)
                except Exception as exc:
                    logger.warning(
                        "material_product_es_sync_failed",
                        product_sn=draft.product_sn,
                        product_name=draft.name,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )

        await session.commit()
    return result


def write_report(report: MaterialScanReport, report_path: Path) -> None:
    payload = {
        "summary": {
            "products": len(report.products),
            "categories": report.category_count,
            "detail_images": report.detail_image_count,
            "main_images": report.main_image_count,
            "matched_main_images": report.matched_main_image_count,
            "unmatched_main_images": len(report.unmatched_main_images),
        },
        "products": [
            {
                **product.model_dump(exclude={"detail_images", "matched_main_images"}, mode="json"),
                "detail_images": [str(path) for path in product.detail_images],
                "matched_main_images": [str(path) for path in product.matched_main_images],
            }
            for product in report.products
        ],
        "unmatched_main_images": [str(path) for path in report.unmatched_main_images],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="导入素材商品目录")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "backend" / "material_catalog_report.json")
    parser.add_argument("--commit", action="store_true", help="写入数据库并复制图片")
    parser.add_argument(
        "--draft",
        action="store_true",
        help="导入为待审核下架商品；默认 --commit 会直接上架并审核通过",
    )
    args = parser.parse_args()

    defaults = load_defaults(args.config.resolve())
    report = scan_materials(args.source.resolve(), defaults)
    write_report(report, args.report.resolve())
    logger.info(
        "material_catalog_scanned",
        products=len(report.products),
        categories=report.category_count,
        detail_images=report.detail_image_count,
        main_images=report.main_image_count,
        matched_main_images=report.matched_main_image_count,
        unmatched_main_images=len(report.unmatched_main_images),
        report=str(args.report.resolve()),
    )
    if not args.commit:
        logger.info("material_catalog_dry_run", hint="确认报告后添加 --commit 执行导入")
        return

    try:
        imported = await import_catalog(report, defaults, publish=not args.draft)
        logger.info("material_catalog_imported", **imported.model_dump())
    finally:
        from app.search.client import close_search_client

        await close_search_client()


if __name__ == "__main__":
    asyncio.run(main())
