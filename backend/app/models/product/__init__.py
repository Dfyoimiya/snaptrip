"""商品域模型包 —— 集中导出所有产品相关 ORM 模型。

Author: SnapTrip Team
Date: 2026-05-26 / 2026-06-16
"""

from app.models.product.attribute import PmsProductAttribute, PmsProductAttributeValue  # noqa: F401
from app.models.product.brand import PmsBrand  # noqa: F401
from app.models.product.category import PmsCategory  # noqa: F401
from app.models.product.cf_vector import PmsProductCFVector  # noqa: F401
from app.models.product.embedding import PmsProductEmbedding  # noqa: F401
from app.models.product.product import PmsProduct  # noqa: F401
from app.models.product.sku import PmsSku  # noqa: F401

__all__ = [
    "PmsCategory",
    "PmsBrand",
    "PmsProduct",
    "PmsSku",
    "PmsProductAttribute",
    "PmsProductAttributeValue",
    "PmsProductCFVector",
    "PmsProductEmbedding",
]
