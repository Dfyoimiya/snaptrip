"""
Phase 6: 会员域集成测试 —— 地址管理 + 收藏 + 管理员会员查询 + 个人信息。

覆盖场景:
  - 地址 CRUD
  - 收藏流程（收藏→查看→取消收藏）
  - 管理员会员列表查询
  - 前台个人信息查看
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# ============================================================================
#  Phase 6: 会员域 — 地址管理 + 收藏 + 管理员会员查询
# ============================================================================


class TestPhase6MemberFlow:
    """端到端: 会员功能"""

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_admin_member_list(self, auth_client: AsyncClient):
        """管理后台: 查看会员列表"""
        resp = await auth_client.get("/api/v1/admin/members")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_member_profile(self, auth_client: AsyncClient, test_user_email: str):
        """前台: 查看个人信息"""
        resp = await auth_client.get("/api/v1/portal/member/profile")
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == test_user_email
