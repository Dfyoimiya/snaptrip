"""商品向量嵌入模型 —— pms_product_embeddings 表。

为语义相似度检索提供商品向量表示, 支持:
  - 基于用户画像的语义商品搜索 (cosine similarity)
  - 相似商品推荐 (同一向量空间中找 nearest neighbors)
  - 多模型版本管理 (model_name + updated_at 追踪嵌入来源)

复用项目已有的 pgvector 扩展 (与 TripHistory.embedding 同模式)。

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


class PmsProductEmbedding(CommerceBase):
    """商品向量嵌入表 —— 每个商品一条记录, 一个 1536 维向量。

    与 pms_products 一对一关系 (product_id UNIQUE)。
    1536 维度匹配 text-embedding-3-small / DeepSeek embedding 等主流模型。
    """

    __tablename__ = "pms_product_embeddings"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pms_products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="商品ID (一对一关系)"
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(384), nullable=False, comment="商品语义向量 (384维)"
    )
    model_name: Mapped[str] = mapped_column(
        String(64), nullable=False, default="all-MiniLM-L6-v2",
        comment="生成嵌入的模型名称"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        comment="嵌入最后更新时间"
    )
