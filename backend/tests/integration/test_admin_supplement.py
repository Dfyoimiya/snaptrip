"""
Admin API 补充测试 —— PUT/DELETE/PATCH 操作.

覆盖:
  - 商品: 编辑/删除/上下架/新品/推荐
  - 品牌: 编辑/删除
  - 优惠券: 编辑/删除
  - 订单: 关闭/发货/列表查询

运行前提: make test-up && make migrate-test
运行命令: cd backend && uv run pytest tests/integration/test_admin_supplement.py -v

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ============================================================================
#  Helpers
# ============================================================================


async def _create_test_product(client: AsyncClient) -> dict:
    """创建完整的商品(含分类+品牌+SKU)，返回 product dict."""
    cat_resp = await client.post(
        "/api/v1/admin/categories",
        json={"name": f"test-cat-{uuid.uuid4().hex[:6]}"},
    )
    assert cat_resp.status_code == 200, cat_resp.text
    cat_id = cat_resp.json()["data"]["id"]

    brand_resp = await client.post(
        "/api/v1/admin/brands",
        json={"name": f"test-brand-{uuid.uuid4().hex[:6]}"},
    )
    assert brand_resp.status_code == 200, brand_resp.text
    brand_id = brand_resp.json()["data"]["id"]

    sku_code = f"SKU-{uuid.uuid4().hex[:6]}"
    prod_resp = await client.post(
        "/api/v1/admin/products",
        json={
            "name": f"test-prod-{uuid.uuid4().hex[:6]}",
            "price": "99.00",
            "category_id": cat_id,
            "brand_id": brand_id,
            "publish_status": 1,
            "skus": [
                {
                    "sku_code": sku_code,
                    "spec": "{}",
                    "price": "99.00",
                    "stock": 100,
                }
            ],
        },
    )
    assert prod_resp.status_code in (200, 201), prod_resp.text
    return prod_resp.json()["data"]


async def _create_order(client: AsyncClient) -> dict:
    """创建一条已支付订单(用于关闭/发货测试)，返回 order dict."""
    product = await _create_test_product(client)
    product_id = product["id"]
    sku_id = product["skus"][0]["id"]

    # 审核通过
    await client.patch(f"/api/v1/admin/products/{product_id}/verify?status=1")

    # 加购
    cart_resp = await client.post(
        "/api/v1/portal/cart",
        json={"product_id": product_id, "sku_id": sku_id, "quantity": 1},
    )
    assert cart_resp.status_code in (200, 201), cart_resp.text
    cart_item_id = cart_resp.json()["data"]["id"]

    # 下单
    order_resp = await client.post(
        "/api/v1/portal/orders",
        json={
            "cart_item_ids": [cart_item_id],
            "receiver_name": "测试用户",
            "receiver_phone": "13800000000",
            "receiver_province": "北京",
            "receiver_city": "北京",
            "receiver_region": "朝阳区",
            "receiver_detail_address": "测试地址",
            "pay_type": 1,
        },
    )
    assert order_resp.status_code in (200, 201), order_resp.text
    return order_resp.json()["data"]


# ============================================================================
#  Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_user_email() -> str:
    return f"admin-suppl-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def auth_client(test_user_email: str):
    """创建已认证的 HTTP 客户端."""
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    # 注册
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": test_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    # 登录
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


# ============================================================================
#  1. 商品管理: PUT/PATCH/DELETE
# ============================================================================


class TestProductSupplement:
    """补充商品管理 Admin API 的写操作测试."""

    async def test_update_product(self, auth_client: AsyncClient):
        """PUT /api/v1/admin/products/{id} —— 编辑商品名称与价格."""
        product = await _create_test_product(auth_client)
        product_id = product["id"]

        new_name = f"updated-{uuid.uuid4().hex[:6]}"
        resp = await auth_client.put(
            f"/api/v1/admin/products/{product_id}",
            json={"name": new_name, "price": "159.00"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["name"] == new_name
        assert data["price"] == "159.00" or str(data["price"]) in ("159.00", "159")

    async def test_delete_product(self, auth_client: AsyncClient):
        """DELETE /api/v1/admin/products/{id} —— 软删除商品."""
        product = await _create_test_product(auth_client)
        product_id = product["id"]

        # 删除
        del_resp = await auth_client.delete(f"/api/v1/admin/products/{product_id}")
        assert del_resp.status_code == 200, del_resp.text
        assert del_resp.json()["message"] == "删除成功"

        # 详情应 404
        get_resp = await auth_client.get(f"/api/v1/admin/products/{product_id}")
        assert get_resp.status_code == 404, f"Expected 404, got {get_resp.status_code}"

    async def test_update_product_status(self, auth_client: AsyncClient):
        """PATCH /api/v1/admin/products/{id}/status —— 上架/下架切换."""
        product = await _create_test_product(auth_client)
        product_id = product["id"]

        # 下架 (status=0)
        resp = await auth_client.patch(
            f"/api/v1/admin/products/{product_id}/status?status=0"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["publish_status"] == 0

        # 上架 (status=1)
        resp = await auth_client.patch(
            f"/api/v1/admin/products/{product_id}/status?status=1"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["publish_status"] == 1

    async def test_update_product_recommend(self, auth_client: AsyncClient):
        """PATCH /api/v1/admin/products/{id}/recommend —— 设为推荐."""
        product = await _create_test_product(auth_client)
        product_id = product["id"]

        # 设为推荐
        resp = await auth_client.patch(
            f"/api/v1/admin/products/{product_id}/recommend?status=1"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["recommend_status"] == 1

        # 取消推荐
        resp = await auth_client.patch(
            f"/api/v1/admin/products/{product_id}/recommend?status=0"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["recommend_status"] == 0

    async def test_update_product_new(self, auth_client: AsyncClient):
        """PATCH /api/v1/admin/products/{id}/new —— 设为新品."""
        product = await _create_test_product(auth_client)
        product_id = product["id"]

        # 设为新品
        resp = await auth_client.patch(
            f"/api/v1/admin/products/{product_id}/new?status=1"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["new_status"] == 1

        # 取消新品
        resp = await auth_client.patch(
            f"/api/v1/admin/products/{product_id}/new?status=0"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["new_status"] == 0


# ============================================================================
#  2. 品牌管理: PUT/DELETE
# ============================================================================


class TestBrandSupplement:
    """补充品牌管理 Admin API 的写操作测试."""

    async def test_update_brand(self, auth_client: AsyncClient):
        """PUT /api/v1/admin/brands/{id} —— 编辑品牌名称."""
        # 创建品牌
        create_resp = await auth_client.post(
            "/api/v1/admin/brands",
            json={"name": "TestBrand", "first_letter": "T", "factory_status": 1},
        )
        assert create_resp.status_code == 200, create_resp.text
        brand_id = create_resp.json()["data"]["id"]

        # 编辑
        update_resp = await auth_client.put(
            f"/api/v1/admin/brands/{brand_id}",
            json={"name": "UpdatedBrand", "first_letter": "U"},
        )
        assert update_resp.status_code == 200, update_resp.text
        data = update_resp.json()["data"]
        assert data["name"] == "UpdatedBrand"
        assert data["first_letter"] == "U"

    async def test_delete_brand(self, auth_client: AsyncClient):
        """DELETE /api/v1/admin/brands/{id} —— 删除品牌."""
        # 创建品牌
        create_resp = await auth_client.post(
            "/api/v1/admin/brands",
            json={"name": "ToDelete", "first_letter": "D"},
        )
        assert create_resp.status_code == 200, create_resp.text
        brand_id = create_resp.json()["data"]["id"]

        # 删除
        del_resp = await auth_client.delete(f"/api/v1/admin/brands/{brand_id}")
        assert del_resp.status_code == 200, del_resp.text

        # 详情应 404
        get_resp = await auth_client.get(f"/api/v1/admin/brands/{brand_id}")
        assert get_resp.status_code == 404, f"Expected 404, got {get_resp.status_code}"


# ============================================================================
#  3. 优惠券管理: PUT/DELETE
# ============================================================================


class TestCouponSupplement:
    """补充优惠券管理 Admin API 的写操作测试."""

    async def test_update_coupon(self, auth_client: AsyncClient):
        """PUT /api/v1/admin/coupons/{id} —— 编辑优惠券名称与金额."""
        # 创建优惠券
        create_resp = await auth_client.post(
            "/api/v1/admin/coupons",
            json={
                "name": "满100减20",
                "type": 0,
                "use_type": 0,
                "amount": "20.00",
                "min_amount": "100.00",
                "count": 1000,
                "per_limit": 1,
            },
        )
        assert create_resp.status_code in (200, 201), create_resp.text
        coupon_id = create_resp.json()["data"]["id"]

        # 编辑
        update_resp = await auth_client.put(
            f"/api/v1/admin/coupons/{coupon_id}",
            json={"name": "满200减50", "amount": "50.00", "min_amount": "200.00"},
        )
        assert update_resp.status_code == 200, update_resp.text
        data = update_resp.json()["data"]
        assert data["name"] == "满200减50"
        assert data["amount"] == "50.00" or str(data["amount"]) in ("50.00", "50")

    async def test_delete_coupon(self, auth_client: AsyncClient):
        """DELETE /api/v1/admin/coupons/{id} —— 删除优惠券."""
        # 创建优惠券
        create_resp = await auth_client.post(
            "/api/v1/admin/coupons",
            json={
                "name": "将被删除的券",
                "type": 0,
                "use_type": 0,
                "amount": "10.00",
                "min_amount": "50.00",
                "count": 100,
                "per_limit": 1,
            },
        )
        assert create_resp.status_code in (200, 201), create_resp.text
        coupon_id = create_resp.json()["data"]["id"]

        # 删除
        del_resp = await auth_client.delete(f"/api/v1/admin/coupons/{coupon_id}")
        assert del_resp.status_code == 200, del_resp.text

        # 详情应 404
        get_resp = await auth_client.get(f"/api/v1/admin/coupons/{coupon_id}")
        assert get_resp.status_code == 404, f"Expected 404, got {get_resp.status_code}"


# ============================================================================
#  4. 订单管理: POST (关闭/发货) + GET 列表
# ============================================================================


class TestOrderSupplement:
    """补充订单管理 Admin API 的操作测试."""

    async def test_close_order(self, auth_client: AsyncClient):
        """POST /api/v1/admin/orders/{id}/close —— 关闭未支付订单."""
        order = await _create_order(auth_client)
        order_id = order["id"]

        # 未支付订单(status=0)可以直接关闭
        close_resp = await auth_client.post(
            f"/api/v1/admin/orders/{order_id}/close?note=test close"
        )
        assert close_resp.status_code == 200, close_resp.text
        assert close_resp.json()["data"]["status"] != 0  # 状态不再是待付款

    async def test_deliver_order(self, auth_client: AsyncClient):
        """POST /api/v1/admin/orders/{id}/delivery —— 发货."""
        order = await _create_order(auth_client)
        order_id = order["id"]

        # 先支付
        pay_resp = await auth_client.post(f"/api/v1/portal/orders/{order_id}/pay")
        assert pay_resp.status_code == 200, pay_resp.text
        assert pay_resp.json()["data"]["status"] == 1  # 已付款

        # 发货
        delivery_resp = await auth_client.post(
            f"/api/v1/admin/orders/{order_id}/delivery",
            json={"delivery_company": "顺丰速运", "delivery_sn": "SF1234567890"},
        )
        assert delivery_resp.status_code == 200, delivery_resp.text
        assert delivery_resp.json()["data"]["status"] == 2  # 已发货
        assert delivery_resp.json()["data"]["delivery_company"] == "顺丰速运"

    async def test_list_admin_orders(self, auth_client: AsyncClient):
        """GET /api/v1/admin/orders —— 管理员可查看所有订单."""
        # 创建一条订单
        await _create_order(auth_client)

        resp = await auth_client.get("/api/v1/admin/orders?page=1&page_size=10")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1


# ============================================================================
#  5. 秒杀管理补充: 删除场次 + 删除秒杀商品
# ============================================================================


class TestFlashSupplement:
    """补充秒杀管理 Admin API 的删除操作."""

    async def test_delete_flash_session(self, auth_client: AsyncClient):
        """DELETE /api/v1/admin/flash-promotions/{p}/sessions/{s} —— 删除场次."""
        now = datetime.now()

        # 创建活动
        promo_resp = await auth_client.post(
            "/api/v1/admin/flash-promotions",
            json={
                "title": "删除场次测试",
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=3)).isoformat(),
            },
        )
        assert promo_resp.status_code in (200, 201), promo_resp.text
        promo_id = promo_resp.json()["data"]["id"]

        # 创建场次
        session_resp = await auth_client.post(
            f"/api/v1/admin/flash-promotions/{promo_id}/sessions",
            json={
                "promotion_id": promo_id,
                "name": "待删除场次",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat(),
            },
        )
        assert session_resp.status_code in (200, 201), session_resp.text
        session_id = session_resp.json()["data"]["id"]

        # 删除场次
        del_resp = await auth_client.delete(
            f"/api/v1/admin/flash-promotions/{promo_id}/sessions/{session_id}"
        )
        assert del_resp.status_code == 200, del_resp.text
        assert del_resp.json()["message"] == "删除成功"

    async def test_delete_flash_promotion(self, auth_client: AsyncClient):
        """DELETE /api/v1/admin/flash-promotions/{id} —— 删除秒杀活动."""
        now = datetime.now()

        # 创建活动
        promo_resp = await auth_client.post(
            "/api/v1/admin/flash-promotions",
            json={
                "title": "待删除活动",
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        )
        assert promo_resp.status_code in (200, 201), promo_resp.text
        promo_id = promo_resp.json()["data"]["id"]

        # 删除活动
        del_resp = await auth_client.delete(
            f"/api/v1/admin/flash-promotions/{promo_id}"
        )
        assert del_resp.status_code == 200, del_resp.text
        assert del_resp.json()["message"] == "删除成功"
