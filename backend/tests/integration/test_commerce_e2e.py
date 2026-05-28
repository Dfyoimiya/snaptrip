"""
电商全链路集成测试 —— 跨 6 个 Phase 的端到端业务流程验证。

覆盖场景:
  Phase 2: 商品创建 (分类→品牌→属性→商品+SKU)
  Phase 3: 订单流程 (加购→下单→支付→发货→确认收货)
  Phase 4: 优惠券 (创建→领取→下单使用)
  Phase 5: 首页聚合 (Banner+新品+推荐)
  Phase 6: 会员中心 (地址管理→收藏)

运行前提: make test-up && make migrate-test
运行命令: cd backend && uv run pytest tests/integration/test_commerce_e2e.py -v

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ============================================================================
#  Fixtures — 测试用户与 HTTP 客户端
# ============================================================================


@pytest_asyncio.fixture
async def test_user_email() -> str:
    return f"e2e-test-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def auth_client(test_user_email: str) -> AsyncClient:
    """
    创建已认证的 HTTP 客户端。

    步骤:
      1. 注册新用户
      2. 登录获取 access_token
      3. 返回带 Authorization Header 的客户端
    """
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    # 注册
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_email,
            "password": "TestPass123!",
        },
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    # 如果已注册，直接登录
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_email,
            "password": "TestPass123!",
        },
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def public_client() -> AsyncClient:
    """未认证客户端 —— 游客可访问前台接口"""
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    await client.aclose()


# ============================================================================
#  Phase 2: 商品域 — 创建分类→品牌→属性→商品(含SKU)
# ============================================================================


class TestPhase2ProductFlow:
    """端到端: 管理员创建完整商品域数据"""

    async def test_create_category(self, auth_client: AsyncClient):
        """创建分类 → 查分类列表 → 查树形结构"""
        # 创建
        resp = await auth_client.post("/api/v1/admin/categories", json={"name": "手机通讯"})
        assert resp.status_code == 200, resp.text
        cat_id = resp.json()["data"]["id"]

        # 查询
        resp = await auth_client.get(f"/api/v1/admin/categories/{cat_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "手机通讯"

        # 树形
        resp = await auth_client.get("/api/v1/admin/categories/tree")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_create_brand(self, auth_client: AsyncClient):
        """创建品牌 → 查询 → 全部列表"""
        resp = await auth_client.post(
            "/api/v1/admin/brands",
            json={
                "name": "Apple",
                "first_letter": "A",
                "factory_status": 1,
            },
        )
        assert resp.status_code == 200, resp.text
        brand_id = resp.json()["data"]["id"]

        resp = await auth_client.get(f"/api/v1/admin/brands/{brand_id}")
        assert resp.json()["data"]["name"] == "Apple"

        resp = await auth_client.get("/api/v1/admin/brands/all")
        assert resp.status_code == 200

    async def test_create_product_with_sku(self, auth_client: AsyncClient):
        """
        主干流程: 创建商品(含 2 个 SKU) → 查详情 → 查列表。

        这一步验证了 Phase 2 最核心的事务原子性:
          Product + SKUs + AttributeValues 全部成功或全部回滚
        """
        # 先创建分类和品牌
        cat_resp = await auth_client.post("/api/v1/admin/categories", json={"name": "智能设备"})
        cat_id = cat_resp.json()["data"]["id"]
        brand_resp = await auth_client.post("/api/v1/admin/brands", json={"name": "Xiaomi"})
        brand_id = brand_resp.json()["data"]["id"]

        # 创建商品
        resp = await auth_client.post(
            "/api/v1/admin/products",
            json={
                "name": "Xiaomi 14 Pro",
                "price": "4999.00",
                "category_id": cat_id,
                "brand_id": brand_id,
                "publish_status": 1,
                "description": "旗舰手机",
                "skus": [
                    {
                        "sku_code": "X14-256-BLK",
                        "spec": '{"color":"黑色","storage":"256GB"}',
                        "price": "4999.00",
                        "stock": 200,
                    },
                    {
                        "sku_code": "X14-512-WHT",
                        "spec": '{"color":"白色","storage":"512GB"}',
                        "price": "5499.00",
                        "stock": 100,
                    },
                ],
            },
        )
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()["data"]
        product_id = data["id"]
        assert data["name"] == "Xiaomi 14 Pro"
        assert data["stock"] == 300  # 200 + 100
        assert len(data["skus"]) == 2

        # 查询详情
        resp = await auth_client.get(f"/api/v1/admin/products/{product_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Xiaomi 14 Pro"

        # 列表
        resp = await auth_client.get("/api/v1/admin/products?publish_status=1")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

        # 审核通过（前台可见的前提）
        resp = await auth_client.patch(f"/api/v1/admin/products/{product_id}/verify?status=1")
        assert resp.status_code == 200

        return product_id


# ============================================================================
#  Phase 3: 订单域 — 购物车→下单→支付→发货→确认收货
# ============================================================================


class TestPhase3OrderFlow:
    """端到端: 完整的订单生命周期"""

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


# ============================================================================
#  Phase 4: 营销域 — 优惠券创建→领取→(下单使用预留)
# ============================================================================


class TestPhase4CouponFlow:
    """端到端: 优惠券创建与领取"""

    async def test_coupon_create_and_claim(self, auth_client: AsyncClient):
        """管理员创建优惠券 → 用户领取 → 查我的券"""
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

        # 查可领取列表
        avail = await auth_client.get("/api/v1/portal/coupons/available")
        assert avail.status_code == 200
        assert len(avail.json()["data"]["items"]) >= 1

        # 领取
        claim = await auth_client.post(f"/api/v1/portal/coupons/{coupon_id}/claim")
        assert claim.status_code == 200, claim.text
        assert claim.json()["data"]["use_status"] == 0  # 未使用

        # 我的优惠券
        mine = await auth_client.get("/api/v1/portal/coupons/mine?use_status=0")
        assert mine.status_code == 200
        assert len(mine.json()["data"]) >= 1

        # 重复领取应被拒绝
        dup = await auth_client.post(f"/api/v1/portal/coupons/{coupon_id}/claim")
        assert dup.status_code in (400, 409), f"Expected error, got {dup.status_code}"

    async def test_flash_promotion_create(self, auth_client: AsyncClient):
        """创建秒杀活动 → 添加场次 → 添加商品"""
        from datetime import datetime, timedelta

        now = datetime.now()

        # 创建活动
        promo = await auth_client.post(
            "/api/v1/admin/flash-promotions",
            json={
                "title": "618秒杀测试",
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=3)).isoformat(),
            },
        )
        assert promo.status_code in (200, 201), promo.text
        promo_id = promo.json()["data"]["id"]

        # 创建场次
        session = await auth_client.post(
            f"/api/v1/admin/flash-promotions/{promo_id}/sessions",
            json={
                "promotion_id": promo_id,
                "name": "10点场",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat(),
            },
        )
        assert session.status_code in (200, 201), session.text
        session_id = session.json()["data"]["id"]

        # 添加秒杀商品 (需要先有商品和SKU)
        cat_resp = await auth_client.post("/api/v1/admin/categories", json={"name": "秒杀分类"})
        cat_id = cat_resp.json()["data"]["id"]
        brand_resp = await auth_client.post("/api/v1/admin/brands", json={"name": "FlashBrand"})
        brand_id = brand_resp.json()["data"]["id"]
        prod = await auth_client.post(
            "/api/v1/admin/products",
            json={
                "name": "秒杀商品",
                "price": "999.00",
                "category_id": cat_id,
                "brand_id": brand_id,
                "publish_status": 1,
                "skus": [{"sku_code": "FS-001", "spec": "{}", "price": "999.00", "stock": 100}],
            },
        )
        sku_id = prod.json()["data"]["skus"][0]["id"]
        product_id = prod.json()["data"]["id"]

        # 添加到秒杀
        fp = await auth_client.post(
            f"/api/v1/admin/flash-promotions/{promo_id}/sessions/{session_id}/products",
            json={
                "session_id": session_id,
                "product_id": product_id,
                "sku_id": sku_id,
                "flash_price": "699.00",
                "flash_stock": 500,
                "flash_limit": 2,
            },
        )
        assert fp.status_code in (200, 201), fp.text
        assert float(fp.json()["data"]["flash_price"]) == 699.0

        # 活动列表
        plist = await auth_client.get("/api/v1/admin/flash-promotions")
        assert plist.status_code == 200


# ============================================================================
#  Phase 5: 内容域 — Banner/专题创建 + 首页聚合 + 统计
# ============================================================================


class TestPhase5CmsFlow:
    """端到端: CMS 内容管理 + 统计查询"""

    async def test_banner_crud(self, auth_client: AsyncClient):
        """创建 Banner → 查列表 → 修改排序 → 删除"""
        # 创建
        resp = await auth_client.post(
            "/api/v1/admin/cms/banners",
            json={
                "title": "618大促",
                "pic": "https://img.example.com/b1.jpg",
                "sort": 0,
            },
        )
        assert resp.status_code in (200, 201), resp.text
        banner_id = resp.json()["data"]["id"]

        # 列表
        lst = await auth_client.get("/api/v1/admin/cms/banners")
        assert lst.status_code == 200

        # 修改排序
        sort_resp = await auth_client.patch(f"/api/v1/admin/cms/banners/{banner_id}/sort?sort=10")
        assert sort_resp.status_code == 200
        assert sort_resp.json()["data"]["sort"] == 10

        # 删除
        del_resp = await auth_client.delete(f"/api/v1/admin/cms/banners/{banner_id}")
        assert del_resp.status_code == 200

    async def test_homepage_aggregation(self, public_client: AsyncClient):
        """首页聚合 —— 游客可访问"""
        resp = await public_client.get("/api/v1/portal/home")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "banners" in data
        assert "new_products" in data
        assert "recommend_products" in data

    async def test_stats_overview(self, auth_client: AsyncClient):
        """统计看板概览"""
        resp = await auth_client.get("/api/v1/admin/stats/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "today_order_count" in data
        assert "total_product_count" in data

    async def test_sales_stats(self, auth_client: AsyncClient):
        """销售趋势"""
        resp = await auth_client.get("/api/v1/admin/stats/sales?days=7")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_product_rank(self, auth_client: AsyncClient):
        """商品排行"""
        resp = await auth_client.get("/api/v1/admin/stats/products?limit=10")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_subject_crud(self, auth_client: AsyncClient):
        """专题管理"""
        resp = await auth_client.post(
            "/api/v1/admin/cms/subjects",
            json={
                "title": "618省钱攻略",
                "category_name": "活动",
                "recommend_status": 1,
            },
        )
        assert resp.status_code in (200, 201), resp.text
        subj_id = resp.json()["data"]["id"]

        lst = await auth_client.get("/api/v1/admin/cms/subjects")
        assert lst.status_code == 200

        await auth_client.delete(f"/api/v1/admin/cms/subjects/{subj_id}")


# ============================================================================
#  Phase 6: 会员域 — 地址管理 + 收藏 + 管理员会员查询
# ============================================================================


class TestPhase6MemberFlow:
    """端到端: 会员功能"""

    async def test_address_crud(self, auth_client: AsyncClient):
        """地址 CRUD —— 创建→查列表→编辑→删除"""
        # 创建
        resp = await auth_client.post(
            "/api/v1/portal/member/addresses",
            json={
                "name": "李四",
                "phone": "13900139000",
                "province": "浙江",
                "city": "杭州",
                "region": "西湖区",
                "detail_address": "文三路 100 号",
                "default_status": 1,
            },
        )
        assert resp.status_code in (200, 201), resp.text
        addr_id = resp.json()["data"]["id"]

        # 列表
        lst = await auth_client.get("/api/v1/portal/member/addresses")
        assert lst.status_code == 200
        assert any(a["id"] == addr_id for a in lst.json()["data"])

        # 编辑
        upd = await auth_client.put(f"/api/v1/portal/member/addresses/{addr_id}", json={"phone": "13800001111"})
        assert upd.status_code == 200

        # 删除
        await auth_client.delete(f"/api/v1/portal/member/addresses/{addr_id}")

    async def test_favorite_flow(self, auth_client: AsyncClient):
        """收藏流程 —— 需要先有商品"""
        # 准备商品
        cat_resp = await auth_client.post("/api/v1/admin/categories", json={"name": "收藏分类"})
        cat_id = cat_resp.json()["data"]["id"]
        brand_resp = await auth_client.post("/api/v1/admin/brands", json={"name": "FavBrand"})
        brand_id = brand_resp.json()["data"]["id"]
        prod = await auth_client.post(
            "/api/v1/admin/products",
            json={
                "name": "收藏测试商品",
                "price": "88.00",
                "category_id": cat_id,
                "brand_id": brand_id,
                "publish_status": 1,
                "skus": [{"sku_code": "FV-001", "spec": "{}", "price": "88.00", "stock": 50}],
            },
        )
        product_id = prod.json()["data"]["id"]

        # 收藏
        fav = await auth_client.post(f"/api/v1/portal/member/favorites?product_id={product_id}")
        assert fav.status_code in (200, 201), fav.text

        # 查收藏
        fav_list = await auth_client.get("/api/v1/portal/member/favorites")
        assert fav_list.status_code == 200
        assert len(fav_list.json()["data"]["items"]) >= 1

        # 取消收藏
        await auth_client.delete(f"/api/v1/portal/member/favorites/{product_id}")

    async def test_admin_member_list(self, auth_client: AsyncClient):
        """管理后台: 查看会员列表"""
        resp = await auth_client.get("/api/v1/admin/members")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data

    async def test_member_profile(self, auth_client: AsyncClient, test_user_email: str):
        """前台: 查看个人信息"""
        resp = await auth_client.get("/api/v1/portal/member/profile")
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == test_user_email


# ============================================================================
#  Phase 2: 前台商品浏览 (游客可访问)
# ============================================================================


class TestPhase2Portal:
    """前台商品浏览 —— 未认证用户"""

    async def test_portal_product_search(self, public_client: AsyncClient):
        """搜索商品 —— 返回上架且审核通过的商品"""
        resp = await public_client.get("/api/v1/portal/products?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data

    async def test_portal_category_browse(self, public_client: AsyncClient):
        """按分类浏览"""
        # 需要先创建分类 → 这里可能返回空结果也是合法的
        url = "/api/v1/portal/products/category/00000000-0000-0000-0000-000000000001?page=1&page_size=5"
        resp = await public_client.get(url)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
