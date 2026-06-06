"""营销域模型包。

Author: SnapTrip Team
Date: 2026-05-26
"""

from app.models.promotion.coupon import SmsCoupon, SmsCouponHistory  # noqa: F401
from app.models.promotion.flash import (  # noqa: F401
    SmsFlashPromotion,
    SmsFlashPromotionProduct,
    SmsFlashPromotionSession,
)

__all__ = [
    "SmsCoupon",
    "SmsCouponHistory",
    "SmsFlashPromotion",
    "SmsFlashPromotionSession",
    "SmsFlashPromotionProduct",
]
