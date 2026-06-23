"""商品与品牌媒体映射测试。"""

from app.data.catalog_media import (
    BRAND_LOGO_ASSETS,
    PRODUCT_IMAGE_ASSETS,
    PRODUCT_IMAGE_KEYS,
    get_brand_logo_path,
    get_product_image_path,
)
from app.data.product_catalog_seed import CATALOG_PRODUCTS


def test_seed_products_have_specific_local_images() -> None:
    """目录种子中的每个商品都应有明确的站内图片。"""

    for product in CATALOG_PRODUCTS:
        expected_path = get_product_image_path(product.name)
        assert product.image_url == expected_path
        assert expected_path.startswith("/images/catalog/products/")


def test_product_image_files_are_unique() -> None:
    """不同媒体资源键不能覆盖同一个本地文件。"""

    file_names = [asset.file_name for asset in PRODUCT_IMAGE_ASSETS.values()]
    assert len(file_names) == len(set(file_names))
    assert set(PRODUCT_IMAGE_KEYS.values()) <= set(PRODUCT_IMAGE_ASSETS)


def test_brand_logo_files_are_unique_and_local() -> None:
    """每个品牌应使用独立且稳定的站内 Logo 路径。"""

    file_names = [asset.file_name for asset in BRAND_LOGO_ASSETS.values()]
    assert len(file_names) == len(set(file_names))
    for brand_name in BRAND_LOGO_ASSETS:
        assert get_brand_logo_path(brand_name).startswith("/images/catalog/brands/")
