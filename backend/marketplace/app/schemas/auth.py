"""认证相关 Pydantic Schemas。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")


class AuthAPIResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    phone_number: str | None = Field(None, min_length=6, max_length=20, description="手机号码（可选）")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PhoneLoginRequest(BaseModel):
    phone_number: str = Field(..., min_length=6, max_length=20)
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="密码重置令牌")
    new_password: str = Field(..., min_length=6, max_length=128)


class UserMeResponse(BaseModel):
    id: str
    email: str
    nickname: str | None = None
    avatar_url: str | None = None
    gender: int | None = None


class AccessMenuItem(BaseModel):
    id: str
    parent_id: str | None = None
    title: str
    name: str | None = None
    icon: str | None = None
    sort: int = 0
    hidden: int = 0


class UserAccessResponse(BaseModel):
    roles: list[str]
    permissions: list[str]
    menus: list[AccessMenuItem]
