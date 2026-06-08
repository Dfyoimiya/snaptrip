"""
Phase 4: 营销域集成测试 —— 优惠券创建与领取 + 秒杀活动管理。

覆盖场景:
  - 优惠券创建→领取→查我的券→重复领取拒绝
  - 秒杀活动创建→场次→添加商品
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


# ============================================================================
#  Phase 4: 营销域 — 优惠券创建→领取→(下单使用预留)
# ============================================================================


class TestPhase4CouponFlow:
    """端到端: 优惠券创建与领取"""

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_flash_promotion_create(self, auth_client: AsyncClient):
        """创建秒杀活动 → 添加场次 → 添加商品"""
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
