"""Commerce data models — SQLAlchemy 2.0 declarative mappings.

Domain packages:
  - rbac: Role / Permission / UserRole
  - product: Category / Brand / Product / SKU / Attribute
  - order: Cart / Order / OrderItem / OrderOperateLog
  - member: Address / Favorite
  - promotion: Coupon / CouponHistory / FlashPromotion
  - cms: Banner / Subject / Help
  - infra: Checkpoint / LLMUsageLog / TripHistory

Import order ensures Alembic discovers all tables.
"""

from app.models.base import AuditMixin, CommerceBase, SoftDeleteMixin  # noqa: I001
from app.models.checkpoint import Checkpoint  # noqa: F401
from app.models.cms import CmsBanner, CmsHelp, CmsSubject  # noqa: F401
from app.models.infra import CsNotification  # noqa: F401
from app.models.llm_usage_log import LLMUsageLog  # noqa: F401
from app.models.member import (  # noqa: F401
    CsAgentStatus,
    CsSessionSummary,
    UmsMemberAddress,
    UmsMemberBehavior,
    UmsMemberFavorite,
    UmsMemberSearchLog,
)
from app.models.order import (  # noqa: F401
    CsConversationMessage,
    OmsCartItem,
    OmsOrder,
    OmsOrderItem,
    OmsOrderOperateLog,
    OmsOrderSetting,
    OmsReturnApply,
    OmsReturnReason,
    OmsSupportTicket,
)
from app.models.product import (  # noqa: F401
    PmsBrand,
    PmsCategory,
    PmsProduct,
    PmsProductAttribute,
    PmsProductAttributeValue,
    PmsProductCFVector,
    PmsProductEmbedding,
    PmsSku,
)
from app.models.promotion import (  # noqa: F401
    SmsCoupon,
    SmsCouponHistory,
    SmsFlashPromotion,
    SmsFlashPromotionProduct,
    SmsFlashPromotionSession,
)
from app.models.menu import Menu, Resource, ResourceCategory, RoleMenu, RoleResource  # noqa: F401
from app.models.rbac import Permission, Role, RolePermission, UserRole  # noqa: F401
from app.models.trip_history import TripHistory  # noqa: F401

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
    "PmsProductCFVector",
    "PmsProductEmbedding",
    "CmsBanner",
    "CmsHelp",
    "CmsSubject",
    "UmsMemberAddress",
    "UmsMemberBehavior",
    "UmsMemberFavorite",
    "UmsMemberSearchLog",
    "CsAgentStatus",
    "CsConversationMessage",
    "CsNotification",
    "CsSessionSummary",
    "OmsCartItem",
    "OmsOrder",
    "OmsOrderItem",
    "OmsOrderOperateLog",
    "OmsOrderSetting",
    "OmsReturnApply",
    "OmsReturnReason",
    "OmsSupportTicket",
    "SmsCoupon",
    "SmsCouponHistory",
    "SmsFlashPromotion",
    "SmsFlashPromotionProduct",
    "SmsFlashPromotionSession",
    "Checkpoint",
    "LLMUsageLog",
    "Menu",
    "Resource",
    "ResourceCategory",
    "RoleMenu",
    "RoleResource",
    "TripHistory",
]
