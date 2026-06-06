"""User domain DTOs — auth, profile, address, favorite."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Auth ──

class RegisterReq(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    password: str = Field(min_length=6, max_length=32)
    nickname: str = Field(min_length=1, max_length=20)
    sms_code: str | None = None


class LoginReq(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    password: str


class RefreshReq(BaseModel):
    refresh_token: str


class TokenResp(BaseModel):
    token: str
    refresh_token: str
    expires_in: int


class LoginResp(BaseModel):
    user_id: str
    token: str
    refresh_token: str
    expires_in: int
    user_info: "UserInfoResp"


# ── Profile ──

class UserInfoResp(BaseModel):
    user_id: str
    phone: str
    nickname: str
    avatar: str | None = None
    gender: Literal["M", "F", "U"] | None = None
    created_at: str


class UserUpdateReq(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=20)
    avatar: str | None = None
    gender: Literal["M", "F", "U"] | None = None


# ── Address ──

class AddressCreateReq(BaseModel):
    contact_name: str = Field(min_length=1, max_length=20)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    province: str
    city: str
    district: str
    detail: str = Field(min_length=1, max_length=200)
    lng: float
    lat: float
    label: str | None = None


class AddressUpdateReq(BaseModel):
    contact_name: str | None = None
    phone: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    detail: str | None = None
    lng: float | None = None
    lat: float | None = None
    label: str | None = None


class AddressResp(BaseModel):
    id: str
    contact_name: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    lng: float
    lat: float
    is_default: bool
    label: str | None = None


# ── Favorite ──

class FavoriteAddReq(BaseModel):
    target_type: Literal["product", "merchant"]
    target_id: str


class FavoriteRemoveReq(BaseModel):
    target_type: Literal["product", "merchant"]
    target_id: str


class FavoriteResp(BaseModel):
    id: str
    target_type: str
    target_id: str
    target_name: str | None = None
    target_image: str | None = None
    created_at: str
