"""数据模型 —— SQLAlchemy 2.0 声明式映射。

marketplace 本地生活服务模型。跨包 relationship（如 Plan ↔ Checkpoint）
在 marketplace 模型全部加载后再导入 agent 模型，以避免循环导入。

Author: SnapTrip Team
Date: 2026-05-17
"""

from marketplace.app.models.base import Base, TimestampMixin, UUIDMixin  # noqa: I001
from marketplace.app.models.plan import Plan
from marketplace.app.models.plan_adjustment import PlanAdjustment
from marketplace.app.models.plan_slot import PlanSlot
from marketplace.app.models.poi import POI
from marketplace.app.models.refresh_token import RefreshToken
from marketplace.app.models.user_profile import UserProfile
from marketplace.app.models.users import User

# Checkpoint 模型已迁移到 LangGraph AsyncPostgresSaver，不再使用自定义模型。
# from app.models.checkpoint import Checkpoint  # noqa: F401, E402

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
