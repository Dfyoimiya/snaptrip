"""电商 ORM 基类 —— CommerceBase + AuditMixin + SoftDeleteMixin。

所有电商模型继承 CommerceBase（独立 DeclarativeBase，避免与 marketplace 的 Base 混淆）。
需要审计字段的继承 AuditMixin，需要软删除的继承 SoftDeleteMixin。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    pass


class CommerceBase(DeclarativeBase):
    """电商独立声明基类 —— 与 marketplace.Base 隔离。

    所有电商表共享此元数据, 可通过 metadata.schema 统一指定 schema。
    默认使用 public schema, 后续迁移可按域拆分为 pms/oms/ums/sms/cms。
    """

    metadata: Any  # Alembic 通过 target_metadata 访问

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return f"<{cls} id={self.id}>"


class AuditMixin:
    """审计混入 —— 记录创建/更新时间, 预留创建人/更新人字段。

    Phase 3+ 将通过 created_by/updated_by 关联管理员用户。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        default=None,
    )


class SoftDeleteMixin:
    """软删除混入 —— 数据标记删除而非物理删除。

    is_deleted=True 时视为已删除, deleted_at 记录删除时间。
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
