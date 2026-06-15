"""
【商品域 Pydantic Schema】— 请求/响应模型

知识点速查：
  - Pydantic v2 model_config: 替代 v1 的 class Config，from_attributes=True 允许从 ORM 对象构造
  - Field(..., description="..."): "..." 是 Ellipsis，表示必填字段
  - model_validator(mode="after"): 在所有字段验证后执行，用于跨字段校验
  - computed_field: 不存数据库的动态计算字段，如 total_pages
  - 为什么不直接在 ORM 层校验？ORM 只描述"数据如何存储"，Schema 描述"数据如何传递"
    Pydantic 比 SQLAlchemy 校验更灵活（自定义规则、错误信息中文化）

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# ============================================================================
#  分类 Schema
# ============================================================================

class CategoryCreate(BaseModel):
    """创建分类 —— 提供 name 必填，其余有默认值"""

    # Field(max_length=64): Pydantic 级别限制，会比 SQLAlchemy String(64) 更早报错
    # 好处: 请求刚进来就拦截，不用等到 DB 层才报唯一约束/长度错误
    name: str = Field(..., min_length=1, max_length=64, description="分类名称")
    parent_id: UUID | None = Field(None, description="父分类ID，NULL=顶级分类")
    level: int = Field(default=0, ge=0, le=3, description="层级")
    sort: int = Field(default=0, ge=0, description="排序值")
    nav_status: int = Field(default=1, ge=0, le=1, description="导航栏显示")
    show_status: int = Field(default=1, ge=0, le=1, description="显示状态")
    icon: str | None = Field(None, max_length=255, description="图标URL")
    keywords: str | None = Field(None, max_length=255, description="SEO关键词")
    description: str | None = Field(None, max_length=500, description="分类描述")


class CategoryUpdate(BaseModel):
    """编辑分类 —— 所有字段可选，只更新传入的字段"""

    name: str | None = Field(None, min_length=1, max_length=64)
    parent_id: UUID | None = None
    level: int | None = Field(None, ge=0, le=3)
    sort: int | None = Field(None, ge=0)
    nav_status: int | None = Field(None, ge=0, le=1)
    show_status: int | None = Field(None, ge=0, le=1)
    icon: str | None = Field(None, max_length=255)
    keywords: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=500)


class CategoryResponse(BaseModel):
    """分类详情/列表项"""

    id: UUID
    name: str
    parent_id: UUID | None = None
    level: int
    sort: int
    nav_status: int
    show_status: int
    icon: str | None = None
    keywords: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # from_attributes=True 在 model_config 中定义 → 允许 ORM 对象直接解构成 Pydantic
    model_config = {"from_attributes": True}


class CategoryTreeResponse(BaseModel):
    """树形分类 —— 用于后台分类管理和前台导航"""

    id: UUID
    name: str
    parent_id: UUID | None = None
    level: int
    sort: int
    nav_status: int
    show_status: int
    icon: str | None = None
    children: list[CategoryTreeResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ============================================================================
#  品牌 Schema
# ============================================================================

class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="品牌名称")
    first_letter: str | None = Field(None, min_length=1, max_length=8, description="首字母")
    sort: int = Field(default=0, ge=0)
    factory_status: int = Field(default=1, ge=0, le=1, description="品牌制造商")
    show_status: int = Field(default=1, ge=0, le=1, description="显示状态")
    logo: str | None = Field(None, max_length=255, description="Logo URL")
    big_pic: str | None = Field(None, max_length=255, description="专区大图")
    brand_story: str | None = Field(None, max_length=2000, description="品牌故事")


class BrandUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    first_letter: str | None = Field(None, max_length=8)
    sort: int | None = Field(None, ge=0)
    factory_status: int | None = Field(None, ge=0, le=1)
    show_status: int | None = Field(None, ge=0, le=1)
    logo: str | None = Field(None, max_length=255)
    big_pic: str | None = Field(None, max_length=255)
    brand_story: str | None = Field(None, max_length=2000)


class BrandResponse(BaseModel):
    id: UUID
    name: str
    first_letter: str | None = None
    sort: int
    factory_status: int
    show_status: int
    logo: str | None = None
    big_pic: str | None = None
    brand_story: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================================
#  商品属性 Schema
# ============================================================================

class ProductAttributeCreate(BaseModel):
    category_id: UUID = Field(..., description="商品分类ID")
    name: str = Field(..., min_length=1, max_length=64, description="属性名称")
    attr_type: int = Field(default=1, ge=0, le=1, description="0=规格 1=参数")
    input_type: int = Field(default=0, ge=0, le=2, description="0=手动 1=单选 2=多选")
    input_list: str | None = Field(None, max_length=255, description="可选值,逗号分隔")
    sort: int = Field(default=0, ge=0)
    filter_type: int = Field(default=0, ge=0, le=1, description="支持筛选")
    search_type: int = Field(default=0, ge=0, le=1, description="支持搜索")
    related_status: int = Field(default=0, ge=0, le=1)
    hand_add_status: int = Field(default=0, ge=0, le=1)


class ProductAttributeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    attr_type: int | None = Field(None, ge=0, le=1)
    input_type: int | None = Field(None, ge=0, le=2)
    input_list: str | None = Field(None, max_length=255)
    sort: int | None = Field(None, ge=0)
    filter_type: int | None = Field(None, ge=0, le=1)
    search_type: int | None = Field(None, ge=0, le=1)
    related_status: int | None = Field(None, ge=0, le=1)
    hand_add_status: int | None = Field(None, ge=0, le=1)


class ProductAttributeResponse(BaseModel):
    id: UUID
    category_id: UUID
    name: str
    attr_type: int
    input_type: int
    input_list: str | None = None
    sort: int
    filter_type: int
    search_type: int
    related_status: int
    hand_add_status: int

    model_config = {"from_attributes": True}


# ============================================================================
#  商品 SKU Schema
# ============================================================================

class SkuCreate(BaseModel):
    """创建 SKU —— 与商品一起创建"""

    sku_code: str = Field(..., min_length=1, max_length=64, description="SKU编码")
    spec: str = Field(..., min_length=1, max_length=255, description="规格JSON")
    price: Decimal = Field(..., ge=0.01, max_digits=10, decimal_places=2, description="售价")
    promotion_price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2, description="促销价")
    stock: int = Field(default=0, ge=0, description="库存")
    low_stock: int = Field(default=0, ge=0, description="预警库存")
    pic: str | None = Field(None, max_length=255, description="SKU图片")


class SkuResponse(BaseModel):
    id: UUID
    product_id: UUID
    sku_code: str
    spec: str
    price: Decimal
    promotion_price: Decimal | None = None
    stock: int
    lock_stock: int
    low_stock: int
    sale_count: int
    pic: str | None = None

    model_config = {"from_attributes": True}


# ============================================================================
#  商品 Schema
# ============================================================================

class ProductCreate(BaseModel):
    """创建商品 —— 含基础信息 + SKU列表 + 属性值列表"""

    name: str = Field(..., min_length=1, max_length=200)
    sub_title: str | None = Field(None, max_length=255)
    brand_id: UUID | None = None
    category_id: UUID | None = None
    product_sn: str | None = Field(None, max_length=64)
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    original_price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    promotion_price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    promotion_start_time: datetime | None = None
    promotion_end_time: datetime | None = None
    promotion_per_limit: int = Field(default=0, ge=0)
    promotion_type: int = Field(default=0, ge=0, le=4)
    publish_status: int = Field(default=0, ge=0, le=1)
    new_status: int = Field(default=0, ge=0, le=1)
    recommend_status: int = Field(default=0, ge=0, le=1)
    description: str | None = Field(None)
    keywords: str | None = Field(None, max_length=255)
    unit: str | None = Field(None, max_length=16)
    weight: float | None = Field(None, ge=0.0)
    service_ids: str | None = Field(None, max_length=255)
    freight_template_id: UUID | None = None
    pics: str | None = Field(None, max_length=1000, description="逗号分隔的图片URL")
    album_pics: str | None = Field(None, max_length=1000)
    default_pic: str | None = Field(None, max_length=255)
    skus: list[SkuCreate] = Field(default_factory=list, description="SKU列表")
    # attribute_values: 属性值列表, key=attribute_id, value=属性值字符串
    attribute_values: dict[str, str] = Field(default_factory=dict, description="属性值映射")

    @model_validator(mode="after")
    def validate_promotion_dates(self):
        if (
            self.promotion_start_time
            and self.promotion_end_time
            and self.promotion_start_time >= self.promotion_end_time
        ):
            raise ValueError("促销开始时间必须早于结束时间")
        return self

    @model_validator(mode="after")
    def validate_promotion_price_requires_dates(self):
        """有促销价必须有促销时间，反之亦然"""
        has_price = self.promotion_price is not None
        has_dates = self.promotion_start_time is not None
        if has_price != has_dates:
            raise ValueError("促销价和促销时间必须同时设置")
        return self


class ProductUpdate(BaseModel):
    """编辑商品 —— 所有字段均可选"""

    name: str | None = Field(None, min_length=1, max_length=200)
    sub_title: str | None = Field(None, max_length=255)
    brand_id: UUID | None = None
    category_id: UUID | None = None
    product_sn: str | None = Field(None, max_length=64)
    price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    original_price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    promotion_price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    promotion_start_time: datetime | None = None
    promotion_end_time: datetime | None = None
    promotion_per_limit: int | None = Field(None, ge=0)
    promotion_type: int | None = Field(None, ge=0, le=4)
    publish_status: int | None = Field(None, ge=0, le=1)
    new_status: int | None = Field(None, ge=0, le=1)
    recommend_status: int | None = Field(None, ge=0, le=1)
    description: str | None = None
    keywords: str | None = Field(None, max_length=255)
    unit: str | None = Field(None, max_length=16)
    weight: float | None = Field(None, ge=0.0)
    service_ids: str | None = Field(None, max_length=255)
    freight_template_id: UUID | None = None
    pics: str | None = Field(None, max_length=1000)
    album_pics: str | None = Field(None, max_length=1000)
    default_pic: str | None = Field(None, max_length=255)


class ProductResponse(BaseModel):
    """商品详情响应 —— 不含 SKU 列表 (需要单独查询)"""

    id: UUID
    name: str
    sub_title: str | None = None
    brand_id: UUID | None = None
    category_id: UUID | None = None
    product_sn: str | None = None
    price: Decimal
    original_price: Decimal | None = None
    promotion_price: Decimal | None = None
    promotion_start_time: datetime | None = None
    promotion_end_time: datetime | None = None
    promotion_per_limit: int
    promotion_type: int
    stock: int
    sale_count: int
    pics: str | None = None
    album_pics: str | None = None
    default_pic: str | None = None
    description: str | None = None
    keywords: str | None = None
    unit: str | None = None
    weight: float | None = None
    publish_status: int
    new_status: int
    recommend_status: int
    preview_status: int
    verify_status: int
    service_ids: str | None = None
    freight_template_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductResponse):
    """商品详情 —— 含 SKU 列表 + 属性值列表"""

    skus: list[SkuResponse] = Field(default_factory=list)
    attribute_values: list[dict] = Field(default_factory=list, description="属性值列表")


# ============================================================================
#  前台商品 Schema (不含后台管理字段)
# ============================================================================

class PortalProductResponse(BaseModel):
    """前台商品响应 —— 排除发布/审核/新品/推荐等后台管理状态字段"""

    id: UUID
    name: str
    sub_title: str | None = None
    brand_id: UUID | None = None
    category_id: UUID | None = None
    product_sn: str | None = None
    price: Decimal
    original_price: Decimal | None = None
    promotion_price: Decimal | None = None
    promotion_start_time: datetime | None = None
    promotion_end_time: datetime | None = None
    promotion_per_limit: int
    promotion_type: int
    stock: int
    sale_count: int
    pics: str | None = None
    album_pics: str | None = None
    default_pic: str | None = None
    description: str | None = None
    keywords: str | None = None
    unit: str | None = None
    weight: float | None = None
    service_ids: str | None = None
    freight_template_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PortalProductDetailResponse(PortalProductResponse):
    """前台商品详情 —— 含 SKU 列表 + 属性值列表"""

    skus: list[SkuResponse] = Field(default_factory=list)
    attribute_values: list[dict] = Field(default_factory=list, description="属性值列表")


class ProductListQuery(BaseModel):
    """商品列表筛选条件"""

    keyword: str | None = Field(None, description="搜索关键词")
    brand_id: UUID | None = None
    category_id: UUID | None = None
    publish_status: int | None = Field(None, ge=0, le=1, description="上架状态")
    verify_status: int | None = Field(None, ge=0, le=2, description="审核状态")
    product_sn: str | None = Field(None, max_length=64, description="货号")
    sort_by: str | None = Field(None, description="排序: create_time/sale_count/price_asc/price_desc")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
