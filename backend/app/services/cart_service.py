"""
【购物车 Service】— 业务逻辑层

知识点速查：
  - 幂等性: 同一用户同一 SKU 重复添加 → 更新数量而非新建条目
    如果不保证幂等: 每次加购都新建记录，用户购车列表会重复显示同一商品
  - 为什么要先查再决定 INSERT 还是 UPDATE？
    用 PostgreSQL ON CONFLICT 也可以，但需要 SKU+user 联合唯一约束
    这里用 ORM 先查后决定，更易读且不需要 DDL 变更

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.order import CartItemCreate, CartItemResponse, CartItemUpdate


class CartService:
    """购物车服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 添加商品到购物车 ──

    async def add(self, user_id: UUID, data: CartItemCreate) -> CartItemResponse:
        """
        添加商品到购物车。

        幂等逻辑: 如果用户购物车已有同 SKU → 数量累加
        如果不存在 → 新建条目
        """
        from app.models.order.cart import OmsCartItem
        from app.models.product.product import PmsProduct
        from app.models.product.sku import PmsSku

        # 校验商品和SKU存在且有效
        product = await self.db.get(PmsProduct, data.product_id)
        if not product or product.is_deleted or product.publish_status != 1:
            from app.core.exceptions import ProductOffShelfError
            raise ProductOffShelfError(str(data.product_id))

        sku = await self.db.get(PmsSku, data.sku_id)
        if not sku or sku.product_id != data.product_id:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(data.sku_id))

        # 检查库存
        if sku.stock - sku.lock_stock < data.quantity:
            from app.core.exceptions import InsufficientStockError
            raise InsufficientStockError(str(data.sku_id), sku.stock - sku.lock_stock, data.quantity)

        # 幂等: 查是否已有该 SKU
        result = await self.db.execute(
            select(OmsCartItem).where(
                OmsCartItem.user_id == user_id,
                OmsCartItem.sku_id == data.sku_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 已存在 → 累加数量
            existing.quantity += data.quantity
            existing.checked = 1
            await self.db.flush()
            await self.db.refresh(existing)
            return CartItemResponse.model_validate(existing)

        # 不存在 → 新建
        cart_item = OmsCartItem(
            user_id=user_id,
            product_id=data.product_id,
            product_name=product.name,
            product_pic=product.default_pic,
            sku_id=data.sku_id,
            sku_code=sku.sku_code,
            spec=sku.spec,
            price=sku.promotion_price if sku.promotion_price else sku.price,
            quantity=data.quantity,
            checked=1,
        )
        self.db.add(cart_item)
        await self.db.flush()
        await self.db.refresh(cart_item)
        return CartItemResponse.model_validate(cart_item)

    # ── 查询购物车列表 ──

    async def list_items(self, user_id: UUID) -> list[CartItemResponse]:
        """获取用户购物车中的所有条目（按添加时间倒序）"""
        from app.models.order.cart import OmsCartItem

        result = await self.db.execute(
            select(OmsCartItem)
            .where(OmsCartItem.user_id == user_id)
            .order_by(OmsCartItem.created_at.desc())
        )
        items = result.scalars().all()
        return [CartItemResponse.model_validate(item) for item in items]

    # ── 修改数量 ──

    async def update_item(self, user_id: UUID, item_id: UUID, data: CartItemUpdate) -> CartItemResponse:
        """
        修改购物车条目 —— 数量或勾选状态。

        使用 update().returning() 实现单次 SQL 完成查找+修改+返回
        如果用 get+修改+flush: 需要两次 IO
        """
        from app.models.order.cart import OmsCartItem

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException
            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)

        stmt = (
            update(OmsCartItem)
            .where(OmsCartItem.id == item_id, OmsCartItem.user_id == user_id)
            .values(**values)
            .returning(OmsCartItem)
        )
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(f"购物车条目 {item_id}")
        return CartItemResponse.model_validate(item)

    # ── 删除 ──

    async def delete_item(self, user_id: UUID, item_id: UUID) -> None:
        from app.models.order.cart import OmsCartItem

        stmt = delete(OmsCartItem).where(
            OmsCartItem.id == item_id,
            OmsCartItem.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        # delete() 返回 CursorResult, rowcount 表示删除行数
        # 如果 rowcount == 0 说明条目不存在或不属于该用户
        if result.rowcount == 0:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(f"购物车条目 {item_id}")

    async def clear_cart(self, user_id: UUID) -> None:
        """清空购物车 —— 下单成功后调用"""
        from app.models.order.cart import OmsCartItem

        await self.db.execute(
            delete(OmsCartItem).where(OmsCartItem.user_id == user_id)
        )
