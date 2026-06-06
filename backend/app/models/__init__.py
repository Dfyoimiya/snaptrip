"""数据模型 —— SQLAlchemy 2.0 声明式映射。

按业务域分包：
  - 计划域: plan, plan_slot, plan_adjustment, poi
  - 用户域: users, user_profile, refresh_token
  - 电商域 (rbac): 角色/权限/用户角色关联
  - 电商域 (product): 商品/分类/品牌/SKU/属性
  - 电商域 (order): 购物车/订单/退货
  - 电商域 (member): 会员/地址/收藏/积分
  - 电商域 (promotion): 优惠券/秒杀

导入顺序确保 Alembic 能发现所有表。

Author: SnapTrip Team
Date: 2026-05-17 / 2026-05-26
"""

from app.models.base import AuditMixin, CommerceBase, SoftDeleteMixin  # noqa: I001
from app.models.checkpoint import Checkpoint  # noqa: F401
from app.models.cms import CmsBanner, CmsHelp, CmsSubject  # noqa: F401
from app.models.llm_usage_log import LLMUsageLog  # noqa: F401
from app.models.member import UmsMemberAddress, UmsMemberFavorite  # noqa: F401
from app.models.order import OmsCartItem, OmsOrder, OmsOrderItem, OmsOrderOperateLog  # noqa: F401
from app.models.plan import Plan  # noqa: F401
from app.models.plan_adjustment import PlanAdjustment  # noqa: F401
from app.models.plan_slot import PlanSlot  # noqa: F401
from app.models.poi import POI  # noqa: F401
from app.models.product import (  # noqa: F401
    PmsBrand,
    PmsCategory,
    PmsProduct,
    PmsProductAttribute,
    PmsProductAttributeValue,
    PmsSku,
)
from app.models.promotion import (  # noqa: F401
    SmsCoupon,
    SmsCouponHistory,
    SmsFlashPromotion,
    SmsFlashPromotionProduct,
    SmsFlashPromotionSession,
)
from app.models.rbac import Permission, Role, RolePermission, UserRole  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.trip_history import TripHistory  # noqa: F401
from app.models.user_profile import UserProfile  # noqa: F401
from app.models.users import User  # noqa: F401

__all__ = [
    "CommerceBase",
    "AuditMixin",
    "SoftDeleteMixin",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "PmsCategory",
    "PmsBrand",
    "PmsProduct",
    "PmsSku",
    "PmsProductAttribute",
    "PmsProductAttributeValue",
    "CmsBanner",
    "CmsHelp",
    "CmsSubject",
    "UmsMemberAddress",
    "UmsMemberFavorite",
    "OmsCartItem",
    "OmsOrder",
    "OmsOrderItem",
    "OmsOrderOperateLog",
    "SmsCoupon",
    "SmsCouponHistory",
    "SmsFlashPromotion",
    "SmsFlashPromotionProduct",
    "SmsFlashPromotionSession",
    "User",
    "UserProfile",
    "Plan",
    "PlanSlot",
    "Checkpoint",
    "PlanAdjustment",
    "POI",
    "LLMUsageLog",
    "RefreshToken",
    "TripHistory",
]
