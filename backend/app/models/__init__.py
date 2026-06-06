"""电商数据模型 —— SQLAlchemy 2.0 声明式映射。

按业务域分包：
  - rbac:    角色/权限/用户角色关联
  - product: 商品/分类/品牌/SKU/属性
  - order:   购物车/订单/退货
  - member:  会员/地址/收藏/积分
  - promotion: 优惠券/秒杀

统一使用 app.models.base.CommerceBase 作为基类。

Author: SnapTrip Team
Date: 2026-05-26
"""

from app.models.base import AuditMixin, CommerceBase, SoftDeleteMixin  # noqa: I001
from app.models.cms import CmsBanner, CmsHelp, CmsSubject  # noqa: F401
from app.models.member import UmsMemberAddress, UmsMemberFavorite  # noqa: F401
from app.models.order import OmsCartItem, OmsOrder, OmsOrderItem, OmsOrderOperateLog  # noqa: F401
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
]
