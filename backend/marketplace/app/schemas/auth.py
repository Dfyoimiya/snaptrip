"""认证相关 Pydantic Schemas。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


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
