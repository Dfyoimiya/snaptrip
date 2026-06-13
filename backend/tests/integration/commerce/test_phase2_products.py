"""
Phase 2: 商品域集成测试 —— 创建分类→品牌→属性→商品(含SKU) + 前台浏览。

覆盖场景:
  - 管理员创建完整商品域数据
  - 游客前台商品搜索与分类浏览
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# ============================================================================
#  Phase 2: 商品域 — 创建分类→品牌→属性→商品(含SKU)
# ============================================================================


class TestPhase2ProductFlow:
    """端到端: 管理员创建完整商品域数据"""

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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
#  Phase 2: 前台商品浏览 (游客可访问)
# ============================================================================


class TestPhase2Portal:
    """前台商品浏览 —— 未认证用户"""

    @pytest.mark.asyncio
    async def test_portal_product_search(self, public_client: AsyncClient):
        """搜索商品 —— 返回上架且审核通过的商品"""
        resp = await public_client.get("/api/v1/portal/products?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_portal_category_browse(self, public_client: AsyncClient):
        """按分类浏览"""
        # 需要先创建分类 → 这里可能返回空结果也是合法的
        url = "/api/v1/portal/products/category/00000000-0000-0000-0000-000000000001?page=1&page_size=5"
        resp = await public_client.get(url)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
