"""认证路由 —— 注册 / 登录 / 刷新 / 登出 / 个人资料。

端点:
    POST /api/v1/auth/register  - 注册
    POST /api/v1/auth/login     - 登录
    POST /api/v1/auth/refresh   - 刷新令牌
    POST /api/v1/auth/logout    - 登出
    GET  /api/v1/auth/me        - 当前用户信息

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import logging
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from snaptrip_shared.core.response import success
from snaptrip_shared.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from snaptrip_shared.db.redis import get_redis_client
from snaptrip_shared.db.session import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marketplace.app.core.rate_limit import (
    login_limiter,
    refresh_limiter,
    register_limiter,
)
from marketplace.app.core.security import (
    create_refresh_token,
    get_current_user,
    revoke_refresh_token,
    verify_refresh_token,
)
from marketplace.app.models.user_profile import UserProfile
from marketplace.app.models.users import User
from marketplace.app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    PhoneLoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserMeResponse,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=dict)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rate_limit=Depends(register_limiter),
) -> dict:
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该邮箱已被注册",
        )

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        hashed_password=hash_password(body.password),
        phone_number=body.phone_number,
    )
    db.add(user)
    await db.flush()

    profile = UserProfile(
        user_id=user.id,
        nickname=body.email.split("@")[0],
    )
    db.add(profile)
    await db.flush()

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id, db)
    await db.commit()

    data: dict[str, Any] = success(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ).model_dump(),
        message="注册成功",
    )
    return data


@router.post("/login", response_model=dict)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rate_limit=Depends(login_limiter),
) -> dict:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id, db)
    await db.commit()

    data: dict[str, Any] = success(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ).model_dump(),
        message="登录成功",
    )
    return data


@router.post("/login/phone", response_model=dict)
async def login_phone(
    body: PhoneLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rate_limit=Depends(login_limiter),
) -> dict:
    result = await db.execute(select(User).where(User.phone_number == body.phone_number))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id, db)
    await db.commit()

    data: dict[str, Any] = success(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ).model_dump(),
        message="登录成功",
    )
    return data


@router.post("/refresh", response_model=dict)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rate_limit=Depends(refresh_limiter),
) -> dict:
    rt = await verify_refresh_token(body.refresh_token, db)
    if rt is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期",
        )

    access_token = create_access_token(data={"sub": str(rt.user_id)})
    new_refresh_token = await create_refresh_token(rt.user_id, db)

    await db.delete(rt)
    await db.commit()

    data: dict[str, Any] = success(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        ).model_dump(),
        message="令牌刷新成功",
    )
    return data


@router.post("/logout", response_model=dict)
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await revoke_refresh_token(body.refresh_token, db)
    await db.commit()
    data: dict[str, Any] = success(message="已登出")
    return data


@router.get("/me", response_model=dict)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _logger.info("[me endpoint] called, user=%s", current_user.email)
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    data: dict[str, Any] = success(
        data=UserMeResponse(
            id=str(current_user.id),
            email=current_user.email,
            nickname=profile.nickname if profile else None,
            avatar_url=profile.avatar_url if profile else None,
            gender=profile.gender if profile else None,
        ).model_dump(),
    )
    return data


@router.post("/change-password", response_model=dict)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """修改密码 —— 需要提供旧密码验证身份。"""
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码不正确",
        )
    current_user.hashed_password = hash_password(body.new_password)
    await db.flush()
    await db.commit()
    data: dict[str, Any] = success(message="密码修改成功")
    return data


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """忘记密码 —— 发送重置链接（Mock：令牌打印到日志）。"""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    # 无论用户是否存在都返回成功，防止邮箱枚举
    if user is not None:
        token = secrets.token_urlsafe(32)
        try:
            redis = await get_redis_client()
            await redis.set(f"pwd_reset:{token}", str(user.id), ex=1800)  # 30 分钟有效
            await redis.close()
        except Exception:
            _logger.exception("Redis 存储重置令牌失败")

        _logger.info(
            "【Mock 密码重置】用户 %s 的重置令牌: %s (30分钟有效)",
            body.email,
            token,
        )

    # 无论用户是否存在都返回成功，防止邮箱枚举
    return success(message="如果该邮箱已注册，重置链接已发送")


@router.post("/reset-password", response_model=dict)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """重置密码 —— 使用令牌验证身份后设置新密码。"""
    user_id_str = None
    try:
        redis = await get_redis_client()
        stored = await redis.get(f"pwd_reset:{body.token}")
        if stored is not None:
            user_id_str = stored.decode("utf-8") if isinstance(stored, bytes) else stored
            await redis.delete(f"pwd_reset:{body.token}")
        await redis.close()
    except Exception:
        _logger.exception("Redis 读取重置令牌失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务暂不可用，请稍后重试",
        ) from None

    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌无效或已过期",
        )

    try:
        uid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌无效",
        ) from None

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不存在",
        )

    user.hashed_password = hash_password(body.new_password)
    await db.flush()
    await db.commit()
    data: dict[str, Any] = success(message="密码重置成功")
    return data
