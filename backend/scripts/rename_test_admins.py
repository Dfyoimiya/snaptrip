"""一键更新测试管理员邮箱为简洁格式。

用法: docker exec -w /app/backend snaptrip-marketplace python -m scripts.rename_test_admins
"""

from __future__ import annotations

import asyncio

from snaptrip_shared.db.session import AsyncSessionLocal
from sqlalchemy import select
from marketplace.app.models.users import User

# 旧邮箱模式 → 新邮箱模式
RENAME_MAP = {
    "super_admin": "super",
    "content_admin": "content",
    "order_admin": "order",
    "product_admin": "product",
    "promotion_admin": "promo",
    "member_admin": "member",
    "viewer": "viewer",
}


async def main():
    async with AsyncSessionLocal() as db:
        updated = 0
        for old_slug, new_slug in RENAME_MAP.items():
            for i in range(1, 4):
                old_email = f"{old_slug}_{i:02d}@mall.com"
                new_email = f"{new_slug}{i:02d}@mall.com"

                result = await db.execute(select(User).where(User.email == new_email))
                if result.scalar_one_or_none():
                    print(f"[SKIP] {new_email} already exists")
                    continue

                result = await db.execute(select(User).where(User.email == old_email))
                user = result.scalar_one_or_none()
                if not user:
                    print(f"[MISS] {old_email} not found")
                    continue

                user.email = new_email
                print(f"[OK] {old_email} → {new_email}")
                updated += 1

        await db.commit()
        print(f"\nDone. Renamed {updated} accounts.")


if __name__ == "__main__":
    asyncio.run(main())
