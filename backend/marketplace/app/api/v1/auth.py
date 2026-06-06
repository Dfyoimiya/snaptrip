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

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from snaptrip_shared.core.response import success
from snaptrip_shared.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from marketplace.app.core.security import (
    create_refresh_token,
    get_current_user,
    revoke_refresh_token,
    verify_refresh_token,
)
from snaptrip_shared.db.session import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marketplace.app.models.user_profile import UserProfile
from marketplace.app.models.users import User
from marketplace.app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserMeResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=dict)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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


@router.post("/refresh", response_model=dict)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
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
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    data: dict[str, Any] = success(
        data=UserMeResponse(
            id=str(current_user.id),
            email=current_user.email,
            nickname=profile.nickname if profile else None,
            avatar_url=profile.avatar_url if profile else None,
        ).model_dump(),
    )
    return data
