"""认证安全模块 —— bcrypt 密码哈希 + JWT 令牌管理。

提供:
- hash_password / verify_password: bcrypt 密码操作
- create_access_token: JWT 生成
- verify_token: JWT 验证

数据库相关的认证函数（create_refresh_token / verify_refresh_token / revoke_refresh_token /
get_current_user）已移至 marketplace.app.core.security。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from snaptrip_shared.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")  # type: ignore[no-any-return]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )  # type: ignore[no-any-return]


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    encoded = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded  # type: ignore[no-any-return]


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload  # type: ignore[no-any-return]
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        ) from None
