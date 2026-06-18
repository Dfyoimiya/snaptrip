"""协同过滤商品向量模型 —— pms_product_cf_vectors 表。

存储 ALS 训练产出的商品隐因子向量 (64维), 用于用户个性化召回。
与 pms_product_embeddings (语义向量) 互补:
  - embedding: 384维语义向量 (text → vector), 用于文本语义相似度
  - cf_vector: 64维隐因子向量 (behavior → vector), 用于协同过滤推荐

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommerceBase


class PmsProductCFVector(CommerceBase):
    """商品协同过滤隐因子向量表 —— 每个商品一条记录, 一个 64 维向量。

    与 pms_products 一对一关系 (product_id UNIQUE)。
    64 维度匹配 ALS 模型的 factors 参数。
    """

    __tablename__ = "pms_product_cf_vectors"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pms_products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="商品ID (一对一关系)",
    )
    cf_vector: Mapped[list[float]] = mapped_column(Vector(64), nullable=False, comment="ALS 协同过滤隐因子向量 (64维)")
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, comment="训练版本标识")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        comment="向量最后更新时间",
    )
