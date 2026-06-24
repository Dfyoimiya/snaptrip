from decimal import Decimal
from pathlib import Path

from app.schemas.material_catalog import MaterialCatalogDefaults
from scripts.import_material_catalog import (
    build_detail_html,
    clean_product_name,
    deterministic_price,
    infer_brand,
    stable_product_sn,
)


def defaults() -> MaterialCatalogDefaults:
    return MaterialCatalogDefaults.model_validate(
        {
            "generic_brand": "其他",
            "brand_aliases": {"MI": "小米", "Nintendo": "任天堂"},
            "categories": {
                "数码产品": {
                    "min_price": "99.00",
                    "max_price": "7999.00",
                    "stock": 80,
                    "low_stock": 10,
                    "unit": "台",
                }
            },
        }
    )


def test_clean_product_name_removes_market_suffix() -> None:
    source = "小米15 12_512 白色【行情 报价 价格 评测】-京东"
    assert clean_product_name(source) == "小米15 12 512 白色"


def test_infer_brand_prefers_parenthesized_alias() -> None:
    assert infer_brand("任天堂（Nintendo）Switch 2 游戏机", defaults()) == "任天堂"


def test_stable_values_are_deterministic() -> None:
    first_sn = stable_product_sn("数码产品", "小米15")
    second_sn = stable_product_sn("数码产品", "小米15")
    first_price = deterministic_price("数码产品", "小米15", defaults())
    second_price = deterministic_price("数码产品", "小米15", defaults())

    assert first_sn == second_sn
    assert first_price == second_price
    assert Decimal("99.00") <= first_price <= Decimal("7999.00")


def test_build_detail_html_escapes_product_content() -> None:
    from app.schemas.material_catalog import MaterialProductDraft

    product = MaterialProductDraft(
        category="数码产品",
        name='<script>alert("x")</script>',
        source_name="source",
        brand="其他",
        product_sn="MAT-123",
        price=Decimal("99.00"),
        original_price=Decimal("109.00"),
        stock=1,
        low_stock=0,
        unit="台",
        summary="<b>summary</b>",
        keywords="数码",
        detail_images=[Path("/tmp/a.jpg")],
    )

    rendered = build_detail_html(product, ["/images/a.jpg"])
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;b&gt;summary&lt;/b&gt;" in rendered
