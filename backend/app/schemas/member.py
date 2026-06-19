"""
【会员域 Pydantic Schema】

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
#  收货地址
# ============================================================================


class AddressCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=1, max_length=32)
    province: str | None = Field(None, max_length=32)
    city: str | None = Field(None, max_length=32)
    region: str | None = Field(None, max_length=32)
    detail_address: str = Field(..., min_length=1, max_length=200)
    post_code: str | None = Field(None, max_length=16)
    default_status: int = Field(default=0, ge=0, le=1)


class AddressUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, min_length=1, max_length=32)
    province: str | None = Field(None, max_length=32)
    city: str | None = Field(None, max_length=32)
    region: str | None = Field(None, max_length=32)
    detail_address: str | None = Field(None, min_length=1, max_length=200)
    post_code: str | None = Field(None, max_length=16)
    default_status: int | None = Field(None, ge=0, le=1)


class AddressResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    province: str | None = None
    city: str | None = None
    region: str | None = None
    detail_address: str = Field(..., serialization_alias="detailAddress")
    post_code: str | None = Field(None, serialization_alias="postCode")
    default_status: int = Field(..., serialization_alias="defaultStatus")
    created_at: datetime | None = Field(None, serialization_alias="createdAt")
    model_config = {"from_attributes": True, "populate_by_name": True}


# ============================================================================
#  收藏
# ============================================================================


class FavoriteResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    product_pic: str | None = None
    product_price: str | None = None
    product_status: int | None = None  # 0=下架 1=上架
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
#  会员管理 (复用 marketplace 的 User/UserProfile)
# ============================================================================


class MemberProfileResponse(BaseModel):
    """会员中心个人信息"""

    id: UUID
    email: str
    is_active: bool
    nickname: str | None = None
    avatar_url: str | None = None
    gender: int | None = None
    created_at: str | None = None
    model_config = {"from_attributes": True}


class MemberProfileUpdate(BaseModel):
    """会员个人信息更新"""

    nickname: str | None = Field(None, min_length=1, max_length=64)
    avatar_url: str | None = Field(None, max_length=512)
    gender: int | None = Field(None, ge=0, le=2, description="0=未知 1=男 2=女")


class MemberAdminResponse(BaseModel):
    """管理后台会员列表项"""

    id: UUID
    email: str
    is_active: bool
    created_at: str | None = None
    model_config = {"from_attributes": True}
