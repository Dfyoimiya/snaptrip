"""素材商品目录导入 Schema。"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field


class CategoryImportDefaults(BaseModel):
    """分类级演示数据默认值。"""

    min_price: Decimal = Field(..., ge=0.01, decimal_places=2)
    max_price: Decimal = Field(..., ge=0.01, decimal_places=2)
    stock: int = Field(default=100, ge=0)
    low_stock: int = Field(default=10, ge=0)
    unit: str = Field(default="件", min_length=1, max_length=16)


class MaterialCatalogDefaults(BaseModel):
    """素材导入 seed 配置。"""

    categories: dict[str, CategoryImportDefaults]
    brand_aliases: dict[str, str] = Field(default_factory=dict)
    generic_brand: str = Field(default="其他", min_length=1, max_length=64)
    services: list[str] = Field(default_factory=lambda: ["正品保障", "七天退换"])


class MaterialProductDraft(BaseModel):
    """从一个详情目录识别出的商品草稿。"""

    category: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=200)
    source_name: str = Field(..., min_length=1)
    brand: str = Field(..., min_length=1, max_length=64)
    product_sn: str = Field(..., min_length=1, max_length=64)
    price: Decimal = Field(..., ge=0.01, decimal_places=2)
    original_price: Decimal = Field(..., ge=0.01, decimal_places=2)
    stock: int = Field(..., ge=0)
    low_stock: int = Field(..., ge=0)
    unit: str = Field(..., min_length=1, max_length=16)
    summary: str = Field(..., min_length=1)
    keywords: str = Field(..., min_length=1, max_length=255)
    detail_images: list[Path] = Field(default_factory=list)
    matched_main_images: list[Path] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class MaterialScanReport(BaseModel):
    """素材扫描结果。"""

    products: list[MaterialProductDraft]
    category_count: int = Field(..., ge=0)
    detail_image_count: int = Field(..., ge=0)
    main_image_count: int = Field(..., ge=0)
    matched_main_image_count: int = Field(..., ge=0)
    unmatched_main_images: list[Path] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class MaterialImportResult(BaseModel):
    """数据库导入统计。"""

    created_products: int = Field(default=0, ge=0)
    updated_products: int = Field(default=0, ge=0)
    created_categories: int = Field(default=0, ge=0)
    created_brands: int = Field(default=0, ge=0)
    copied_assets: int = Field(default=0, ge=0)

