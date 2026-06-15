"""认证安全扩展 —— 数据库相关的认证函数。

这些函数依赖 marketplace 的 ORM 模型，因此放在 backend 层而非 shared。

提供:
- oauth2_scheme: FastAPI OAuth2 Bearer 依赖
- create_refresh_token / verify_refresh_token / revoke_refresh_token
- get_current_user: FastAPI 依赖

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from snaptrip_shared.core.config import settings
from snaptrip_shared.db.session import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marketplace.app.models.refresh_token import RefreshToken
from marketplace.app.models.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def create_refresh_token(user_id: uuid.UUID, db: AsyncSession) -> str:
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(rt)
    await db.flush()
    return raw_token


async def verify_refresh_token(raw_token: str, db: AsyncSession) -> RefreshToken | None:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if rt is None:
        return None
    if rt.expires_at < datetime.now(UTC):
        await db.delete(rt)
        await db.flush()
        return None
    return rt  # type: ignore[no-any-return]


async def revoke_refresh_token(raw_token: str, db: AsyncSession) -> None:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if rt:
        await db.delete(rt)
        await db.flush()


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    import logging

    _logger = logging.getLogger(__name__)
    if token is None:
        _logger.warning("[get_current_user] No token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
        )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        _logger.warning("[get_current_user] JWT decode failed, key=%s...", settings.JWT_SECRET_KEY[:8])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        ) from None
    user_id_str: str | None = payload.get("sub")
    _logger.info("[get_current_user] JWT valid, sub=%s", user_id_str)
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式无效",
        )
    try:
        uid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式无效",
        ) from None
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        _logger.warning(
            "[get_current_user] User not found or inactive: id=%s, exists=%s, active=%s",
            user_id_str,
            user is not None,
            user.is_active if user else "N/A",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
        )
    return user  # type: ignore[no-any-return]
