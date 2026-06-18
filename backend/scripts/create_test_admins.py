"""批量创建各角色测试管理员账号。

用法: docker exec snaptrip-marketplace python /app/scripts/create_test_admins.py
"""

from __future__ import annotations

import asyncio
import uuid

from snaptrip_shared.core.security import hash_password
from snaptrip_shared.db.session import AsyncSessionLocal
from sqlalchemy import select

from app.models.rbac import Role, UserRole
from marketplace.app.models.user_profile import UserProfile
from marketplace.app.models.users import User

ROLES = [
    ("super_admin", "super123"),
    ("content_admin", "content123"),
    ("order_admin", "order123"),
    ("product_admin", "product123"),
    ("promotion_admin", "promotion123"),
    ("member_admin", "member123"),
    ("viewer", "viewer123"),
]

ADMINS_PER_ROLE = 3


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Role))
        all_roles = {r.name: r for r in result.scalars().all()}

        created = 0
        for role_name, password_prefix in ROLES:
            role = all_roles.get(role_name)
            if not role:
                print(f"[WARN] 角色 {role_name} 不存在，跳过")
                continue

            for i in range(1, ADMINS_PER_ROLE + 1):
                email = f"{role_name}_{i:02d}@mall.com"
                password = password_prefix  # already the full password

                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    user.hashed_password = hash_password(password)
                    print(f"[UPDATED] {email} → {password}")
                    created += 1
                    continue

                user = User(
                    id=uuid.uuid4(),
                    email=email,
                    hashed_password=hash_password(password),
                    is_active=True,
                )
                db.add(user)
                await db.flush()

                db.add(UserRole(user_id=user.id, role_id=role.id))
                db.add(UserProfile(user_id=user.id, nickname=email.split("@")[0]))
                await db.flush()

                print(f"[OK] {email} / {password} → {role_name}")
                created += 1

        await db.commit()
        print(f"\nDone. Created {created} accounts.")


if __name__ == "__main__":
    asyncio.run(main())
