"""
【会员 Service】— 地址管理 / 收藏 / 管理后台会员

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.member import (
    AddressCreate,
    AddressResponse,
    AddressUpdate,
    FavoriteResponse,
    MemberAdminResponse,
    MemberProfileResponse,
)


class MemberService:
    """会员服务 —— 地址 / 收藏 / 管理"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    #  收货地址
    # =========================================================================

    async def create_address(self, user_id: UUID, data: AddressCreate) -> AddressResponse:
        from app.models.member.member import UmsMemberAddress

        # 如果设为默认，先取消该用户其他默认地址
        if data.default_status == 1:
            await self.db.execute(
                update(UmsMemberAddress).where(UmsMemberAddress.user_id == user_id).values(default_status=0)
            )

        addr = UmsMemberAddress(user_id=user_id, **data.model_dump())
        self.db.add(addr)
        await self.db.flush()
        await self.db.refresh(addr)
        return AddressResponse.model_validate(addr)

    async def update_address(self, user_id: UUID, addr_id: UUID, data: AddressUpdate) -> AddressResponse:
        from app.models.member.member import UmsMemberAddress

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)

        if values.get("default_status") == 1:
            await self.db.execute(
                update(UmsMemberAddress).where(UmsMemberAddress.user_id == user_id).values(default_status=0)
            )

        stmt = (
            update(UmsMemberAddress)
            .where(UmsMemberAddress.id == addr_id, UmsMemberAddress.user_id == user_id)
            .values(**values)
            .returning(UmsMemberAddress)
        )
        result = await self.db.execute(stmt)
        addr = result.scalar_one_or_none()
        if not addr:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(addr_id))
        return AddressResponse.model_validate(addr)

    async def delete_address(self, user_id: UUID, addr_id: UUID) -> None:
        from app.models.member.member import UmsMemberAddress

        result = await self.db.execute(
            delete(UmsMemberAddress).where(
                UmsMemberAddress.id == addr_id,
                UmsMemberAddress.user_id == user_id,
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(addr_id))

    async def list_addresses(self, user_id: UUID) -> list[AddressResponse]:
        from app.models.member.member import UmsMemberAddress

        result = await self.db.execute(
            select(UmsMemberAddress)
            .where(UmsMemberAddress.user_id == user_id)
            .order_by(UmsMemberAddress.default_status.desc(), UmsMemberAddress.created_at.desc())
        )
        return [AddressResponse.model_validate(a) for a in result.scalars().all()]

    # =========================================================================
    #  收藏夹
    # =========================================================================

    async def add_favorite(self, user_id: UUID, product_id: UUID) -> FavoriteResponse:
        from app.models.member.member import UmsMemberFavorite
        from app.models.product.product import PmsProduct

        product = await self.db.get(PmsProduct, product_id)
        if not product or product.is_deleted:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(product_id))

        # 幂等: 已收藏则直接返回
        existing = await self.db.execute(
            select(UmsMemberFavorite).where(
                UmsMemberFavorite.user_id == user_id,
                UmsMemberFavorite.product_id == product_id,
            )
        )
        fav = existing.scalar_one_or_none()
        if fav:
            return FavoriteResponse.model_validate(fav)

        fav = UmsMemberFavorite(
            user_id=user_id,
            product_id=product_id,
            product_name=product.name,
            product_pic=product.default_pic,
            product_price=str(product.price),
        )
        self.db.add(fav)
        await self.db.flush()
        await self.db.refresh(fav)
        return FavoriteResponse.model_validate(fav)

    async def remove_favorite(self, user_id: UUID, product_id: UUID) -> None:
        from app.models.member.member import UmsMemberFavorite

        await self.db.execute(
            delete(UmsMemberFavorite).where(
                UmsMemberFavorite.user_id == user_id,
                UmsMemberFavorite.product_id == product_id,
            )
        )

    async def list_favorites(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[FavoriteResponse], int]:
        from app.models.member.member import UmsMemberFavorite

        base = select(UmsMemberFavorite).where(UmsMemberFavorite.user_id == user_id)
        cnt = select(func.count(UmsMemberFavorite.id)).where(UmsMemberFavorite.user_id == user_id)
        result = await self.db.execute(cnt)
        total = result.scalar() or 0
        result = await self.db.execute(
            base.order_by(UmsMemberFavorite.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return [FavoriteResponse.model_validate(f) for f in result.scalars().all()], total

    # =========================================================================
    #  管理后台: 会员列表 (复用 marketplace User)
    # =========================================================================

    async def list_admin(
        self, keyword: str | None = None, is_active: bool | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[MemberAdminResponse], int]:
        from marketplace.app.models.users import User

        base = select(User)
        cnt = select(func.count(User.id))
        if keyword:
            base = base.where(User.email.ilike(f"%{keyword}%"))
            cnt = cnt.where(User.email.ilike(f"%{keyword}%"))
        if is_active is not None:
            base = base.where(User.is_active == is_active)
            cnt = cnt.where(User.is_active == is_active)

        result = await self.db.execute(cnt)
        total = result.scalar() or 0
        result = await self.db.execute(
            base.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            MemberAdminResponse(
                id=u.id,
                email=u.email,
                is_active=u.is_active,  # type: ignore[attr-defined]
                created_at=str(u.created_at) if u.created_at else None,  # type: ignore[attr-defined]
            )
            for u in result.scalars().all()
        ]
        return items, total

    async def get_member_detail(self, user_id: UUID) -> dict:
        from marketplace.app.models.user_profile import UserProfile
        from marketplace.app.models.users import User

        user = await self.db.get(User, user_id)
        if not user:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(user_id))

        profile_result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()

        return {
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "created_at": str(user.created_at) if user.created_at else None,
            "nickname": profile.nickname if profile else None,
            "avatar_url": profile.avatar_url if profile else None,
            "gender": profile.gender if profile else None,
        }

    async def toggle_member_status(self, user_id: UUID, is_active: bool) -> dict:
        from marketplace.app.models.users import User

        stmt = update(User).where(User.id == user_id).values(is_active=is_active).returning(User)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(user_id))
        return {"id": str(user.id), "email": user.email, "is_active": user.is_active}

    async def update_profile(self, user_id: UUID, data) -> MemberProfileResponse:
        """更新会员个人资料（昵称、头像）。"""
        from marketplace.app.models.user_profile import UserProfile

        result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if not profile:
            # 如果还没有 profile，创建一个
            from marketplace.app.models.users import User

            user = await self.db.get(User, user_id)
            if not user:
                from app.core.exceptions import ProductNotFoundError

                raise ProductNotFoundError(str(user_id))
            profile = UserProfile(user_id=user_id, nickname=user.email.split("@")[0])
            self.db.add(profile)
            await self.db.flush()

        if data.nickname is not None:
            profile.nickname = data.nickname
        if data.avatar_url is not None:
            profile.avatar_url = data.avatar_url
        if data.gender is not None:
            profile.gender = data.gender

        await self.db.flush()
        await self.db.refresh(profile)

        return MemberProfileResponse(
            id=profile.user_id,
            email="",  # will be populated in route handler
            is_active=True,
            nickname=profile.nickname,
            avatar_url=profile.avatar_url,
            gender=profile.gender,
            created_at=None,
        )

    async def get_profile(self, user_id: UUID) -> MemberProfileResponse:
        from marketplace.app.models.user_profile import UserProfile
        from marketplace.app.models.users import User

        user = await self.db.get(User, user_id)
        if not user:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(user_id))

        profile_result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()

        return MemberProfileResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            nickname=profile.nickname if profile else None,
            avatar_url=profile.avatar_url if profile else None,
            gender=profile.gender if profile else None,
            created_at=str(user.created_at) if user.created_at else None,
        )

    # =========================================================================
    #  仪表盘统计
    # =========================================================================

    async def count_new_today(self) -> int:
        """今日新增会员数"""
        from datetime import date

        from marketplace.app.models.users import User

        today = date.today()
        result = await self.db.execute(select(func.count(User.id)).where(User.created_at >= today))
        return result.scalar() or 0
