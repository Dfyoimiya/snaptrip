"""团队开发共享种子数据 — 幂等、可重复执行。

一键创建开发所需的用户、菜单、商品等数据。

用法: cd backend && uv run python scripts/seed_dev.py
"""

import asyncio
import os
import sys
from pathlib import Path

os.environ["APP_ENV"] = "development"

# 确保可以 import 同目录下的 seed_commerce
sys.path.insert(0, str(Path(__file__).parent))


# ====================================================================
# 菜单数据（与 frontend/src/stores/user.ts 的 DEFAULT_MENUS 保持一致）
# ====================================================================
# (frontend_id, parent_frontend_id, title, name, icon, sort, hidden, level)
CANONICAL_MENUS = [
    (1,  0,  "商品管理", "pms",            "Goods",        5, 0, 0),
    (2,  1,  "商品列表", "product",        "List",         4, 0, 1),
    (3,  1,  "添加商品", "addProduct",     "Plus",         3, 0, 1),
    (4,  1,  "商品分类", "productCate",    "FolderOpened", 2, 0, 1),
    (5,  1,  "商品类型", "productAttr",    "Collection",   1, 0, 1),
    (13, 1,  "品牌管理", "brand",          "Trophy",       0, 0, 1),
    (6,  0,  "订单管理", "oms",            "Document",     4, 0, 0),
    (7,  6,  "订单列表", "order",          "List",         3, 0, 1),
    (8,  6,  "订单设置", "orderSetting",   "Setting",      2, 0, 1),
    (9,  6,  "退货申请", "returnApply",    "RefreshLeft",  1, 0, 1),
    (14, 6,  "退货原因", "returnReason",   "Warning",      0, 0, 1),
    (10, 0,  "会员管理", "ums",            "User",         3, 0, 0),
    (11, 10, "用户管理", "admin",          "UserFilled",   4, 0, 1),
    (12, 10, "角色管理", "role",           "Medal",        3, 0, 1),
    (15, 10, "菜单管理", "menu",           "Menu",         2, 0, 1),
    (16, 10, "资源管理", "resource",       "Collection",   1, 0, 1),
    (17, 10, "会员列表", "member",         "List",         0, 0, 1),
    (18, 0,  "营销管理", "sms",            "Promotion",    2, 0, 0),
    (19, 18, "优惠券",   "coupon",         "Ticket",       2, 0, 1),
    (20, 18, "秒杀活动", "flash",          "Timer",        1, 0, 1),
    (21, 18, "品牌推荐", "brandRecommend", "Trophy",       0, 0, 1),
    (22, 0,  "内容管理", "cms",            "DocumentCopy", 1, 0, 0),
    (23, 22, "轮播广告", "banner",         "Picture",      1, 0, 1),
    (24, 22, "专题管理", "subject",        "Notebook",     0, 0, 1),
    (25, 0,  "系统设置", "setting",        "Tools",        0, 0, 0),
    (26, 25, "文件存储", "oss",            "UploadFilled", 0, 0, 1),
]

# ====================================================================
# 开发用户
# ====================================================================
DEV_USERS = [
    ("admin@snaptrip.com", "admin123", "super_admin"),
    ("user@snaptrip.com",  "user123",  None),
]


# ====================================================================
# Seed 函数
# ====================================================================

async def seed_users(session):
    """创建开发用户并分配角色（幂等）。"""
    from marketplace.app.models.users import User
    from app.models.rbac import Role, UserRole
    from snaptrip_shared.core.security import hash_password
    from sqlalchemy import select

    for email, password, role_name in DEV_USERS:
        result = await session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f"  User '{email}' already exists — skipping.")
            continue

        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
        )
        session.add(user)
        await session.flush()  # 获取 user.id（UUID）

        if role_name:
            result = await session.execute(select(Role).where(Role.name == role_name))
            role = result.scalar_one_or_none()
            if role is None:
                print(f"  WARNING: Role '{role_name}' not found — skipping role assignment for {email}")
                continue

            result = await session.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == role.id,
                )
            )
            if result.scalar_one_or_none() is None:
                session.add(UserRole(user_id=user.id, role_id=role.id))

        label = f" (role: {role_name})" if role_name else ""
        print(f"  Created user: {email}{label}")


async def seed_menus(session):
    """插入前端 DEFAULT_MENUS 到 ums_menus 表（幂等、两阶段）。"""
    from app.models.menu import Menu
    from sqlalchemy import select

    result = await session.execute(select(Menu).limit(1))
    if result.scalar_one_or_none():
        print("  Menus already exist — skipping.")
        return

    # Phase 1: 插入所有菜单（parent_id=NULL），记录 frontend_id → db_uuid 映射
    id_map: dict[int, "uuid.UUID"] = {}
    import uuid as _uuid

    for fe_id, _parent_fe_id, title, name, icon, sort, hidden, level in CANONICAL_MENUS:
        menu = Menu(
            id=_uuid.uuid4(),
            title=title,
            name=name,
            icon=icon,
            sort=sort,
            hidden=hidden,
            level=level,
            parent_id=None,  # Phase 2 再修正
        )
        session.add(menu)
        await session.flush()
        id_map[fe_id] = menu.id

    # Phase 2: 修正 parent_id 引用
    for _fe_id, parent_fe_id, _title, _name, _icon, _sort, _hidden, _level in CANONICAL_MENUS:
        if parent_fe_id != 0:
            menu = await session.get(Menu, id_map[_fe_id])
            if menu:
                menu.parent_id = id_map[parent_fe_id]

    print(f"  Menus: {len(CANONICAL_MENUS)} seeded")


async def seed_commerce(session):
    """委托 commerce 种子数据（商品/品牌/分类/优惠券等）。"""
    from seed_commerce import seed as commerce_seed  # noqa: PLC0415
    await commerce_seed(session=session)


# ====================================================================
# 主入口
# ====================================================================

async def seed():
    from snaptrip_shared.db.session import AsyncSessionLocal  # noqa: PLC0415

    async with AsyncSessionLocal() as session:
        try:
            print("Dev seed: creating users...")
            await seed_users(session)

            print("Dev seed: creating menus...")
            await seed_menus(session)

            print("Dev seed: creating commerce data...")
            await seed_commerce(session)

            await session.commit()
            print("\n Dev seed complete!")
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed())
