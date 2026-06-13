"""
Phase 3: 订单域集成测试 —— 购物车→下单→支付→发货→确认收货。

覆盖场景:
  - 完整订单生命周期
  - 购物车修改（数量、勾选、删除）
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient

# ============================================================================
#  Phase 3: 订单域 — 购物车→下单→支付→发货→确认收货
# ============================================================================


class TestPhase3OrderFlow:
    """端到端: 完整的订单生命周期"""

    @pytest.mark.asyncio
    async def test_cart_and_order_flow(self, auth_client: AsyncClient, test_user_email: str):
        """
        核心流程:
          1. 创建商品 + SKU
          2. 加入购物车
          3. 查购物车
          4. 提交订单
          5. 支付
          6. 发货
          7. 确认收货
        """
        # 步骤1: 准备商品
        cat_resp = await auth_client.post("/api/v1/admin/categories", json={"name": "订单测试分类"})
        cat_id = cat_resp.json()["data"]["id"]
        brand_resp = await auth_client.post("/api/v1/admin/brands", json={"name": "OrderTest"})
        brand_id = brand_resp.json()["data"]["id"]

        prod_resp = await auth_client.post(
            "/api/v1/admin/products",
            json={
                "name": "订单测试商品",
                "price": "199.00",
                "category_id": cat_id,
                "brand_id": brand_id,
                "publish_status": 1,
                "skus": [{"sku_code": "OT-001", "spec": "{}", "price": "199.00", "stock": 500}],
            },
        )
        assert prod_resp.status_code in (200, 201), prod_resp.text
        product_id = prod_resp.json()["data"]["id"]
        sku_id = prod_resp.json()["data"]["skus"][0]["id"]

        # 审核通过
        await auth_client.patch(f"/api/v1/admin/products/{product_id}/verify?status=1")

        # 步骤2: 加入购物车
        cart_resp = await auth_client.post(
            "/api/v1/portal/cart",
            json={
                "product_id": product_id,
                "sku_id": sku_id,
                "quantity": 2,
            },
        )
        assert cart_resp.status_code in (200, 201), cart_resp.text
        cart_item_id = cart_resp.json()["data"]["id"]
        assert cart_resp.json()["data"]["quantity"] == 2

        # 步骤3: 查购物车
        list_resp = await auth_client.get("/api/v1/portal/cart")
        assert list_resp.status_code == 200
        assert len(list_resp.json()["data"]) >= 1

        # 步骤4: 提交订单
        order_resp = await auth_client.post(
            "/api/v1/portal/orders",
            json={
                "cart_item_ids": [cart_item_id],
                "receiver_name": "张三",
                "receiver_phone": "13800138000",
                "receiver_province": "北京",
                "receiver_city": "北京",
                "receiver_region": "朝阳区",
                "receiver_detail_address": "望京SOHO T1",
                "pay_type": 1,
            },
        )
        assert order_resp.status_code in (200, 201), order_resp.text
        order_data = order_resp.json()["data"]
        order_id = order_data["id"]
        assert order_data["status"] == 0  # 待付款
        assert Decimal(order_data["total_amount"]) == Decimal("398.00")  # 199 x 2
        assert len(order_data["items"]) == 1

        # 验证购物车已清空(该条目)
        cart_after = await auth_client.get("/api/v1/portal/cart")
        remaining_ids = [i["id"] for i in cart_after.json()["data"]]
        assert cart_item_id not in remaining_ids

        # 步骤5: 支付
        pay_resp = await auth_client.post(f"/api/v1/portal/orders/{order_id}/pay")
        assert pay_resp.status_code == 200, pay_resp.text
        assert pay_resp.json()["data"]["status"] == 1  # 已付款

        # 步骤6: 管理员发货
        delivery_resp = await auth_client.post(
            f"/api/v1/admin/orders/{order_id}/delivery",
            json={
                "delivery_company": "顺丰速运",
                "delivery_sn": "SF1234567890",
            },
        )
        assert delivery_resp.status_code == 200, delivery_resp.text
        assert delivery_resp.json()["data"]["status"] == 2  # 已发货

        # 步骤7: 确认收货
        confirm_resp = await auth_client.post(f"/api/v1/portal/orders/{order_id}/confirm-receipt")
        assert confirm_resp.status_code == 200, confirm_resp.text
        assert confirm_resp.json()["data"]["status"] == 3  # 已收货

        # 验证订单列表
        my_orders = await auth_client.get("/api/v1/portal/orders?status=3")
        assert my_orders.status_code == 200
        assert len(my_orders.json()["data"]["items"]) >= 1

    @pytest.mark.asyncio
    async def test_cart_modify(self, auth_client: AsyncClient):
        """修改购物车数量 → 取消勾选 → 删除"""
        # 准备
        cat_resp = await auth_client.post("/api/v1/admin/categories", json={"name": "购物车测试"})
        cat_id = cat_resp.json()["data"]["id"]
        brand_resp = await auth_client.post("/api/v1/admin/brands", json={"name": "CartTest"})
        brand_id = brand_resp.json()["data"]["id"]
        prod_resp = await auth_client.post(
            "/api/v1/admin/products",
            json={
                "name": "购物车测试商品",
                "price": "50.00",
                "category_id": cat_id,
                "brand_id": brand_id,
                "publish_status": 1,
                "skus": [{"sku_code": "CT-001", "spec": "{}", "price": "50.00", "stock": 100}],
            },
        )
        await auth_client.patch(f"/api/v1/admin/products/{prod_resp.json()['data']['id']}/verify?status=1")
        sku_id = prod_resp.json()["data"]["skus"][0]["id"]
        product_id = prod_resp.json()["data"]["id"]

        # 加购
        cart = await auth_client.post(
            "/api/v1/portal/cart", json={"product_id": product_id, "sku_id": sku_id, "quantity": 3}
        )
        item_id = cart.json()["data"]["id"]

        # 修改数量
        upd = await auth_client.put(f"/api/v1/portal/cart/{item_id}", json={"quantity": 5})
        assert upd.json()["data"]["quantity"] == 5

        # 取消勾选
        unchk = await auth_client.patch(f"/api/v1/portal/cart/{item_id}/checked?checked=0")
        assert unchk.json()["data"]["checked"] == 0

        # 删除
        await auth_client.delete(f"/api/v1/portal/cart/{item_id}")
