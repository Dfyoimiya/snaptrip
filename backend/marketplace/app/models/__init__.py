"""数据模型 —— SQLAlchemy 2.0 声明式映射。

导入顺序确保 Alembic 能发现所有表。

Author: SnapTrip Team
Date: 2026-05-17
"""

from marketplace.app.models.base import Base, TimestampMixin, UUIDMixin
from marketplace.app.models.plan import Plan
from marketplace.app.models.plan_adjustment import PlanAdjustment
from marketplace.app.models.plan_slot import PlanSlot
from marketplace.app.models.poi import POI
from marketplace.app.models.refresh_token import RefreshToken
from marketplace.app.models.user_profile import UserProfile
from marketplace.app.models.users import User

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "UserProfile",
    "Plan",
    "PlanSlot",
    "PlanAdjustment",
    "POI",
    "RefreshToken",
]
