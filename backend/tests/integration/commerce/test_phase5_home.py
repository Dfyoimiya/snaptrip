"""
Phase 5: 内容域集成测试 —— Banner/专题创建 + 首页聚合 + 统计。

覆盖场景:
  - Banner CRUD
  - 首页聚合（游客可访问）
  - 统计看板概览、销售趋势、商品排行
  - 专题管理
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ============================================================================
#  Phase 5: 内容域 — Banner/专题创建 + 首页聚合 + 统计
# ============================================================================


class TestPhase5CmsFlow:
    """端到端: CMS 内容管理 + 统计查询"""

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_homepage_aggregation(self, public_client: AsyncClient):
        """首页聚合 —— 游客可访问"""
        resp = await public_client.get("/api/v1/portal/home")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "banners" in data
        assert "new_products" in data
        assert "recommend_products" in data

    @pytest.mark.asyncio
    async def test_stats_overview(self, auth_client: AsyncClient):
        """统计看板概览"""
        resp = await auth_client.get("/api/v1/admin/stats/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "today_order_count" in data
        assert "total_product_count" in data

    @pytest.mark.asyncio
    async def test_sales_stats(self, auth_client: AsyncClient):
        """销售趋势"""
        resp = await auth_client.get("/api/v1/admin/stats/sales?days=7")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    @pytest.mark.asyncio
    async def test_product_rank(self, auth_client: AsyncClient):
        """商品排行"""
        resp = await auth_client.get("/api/v1/admin/stats/products?limit=10")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    @pytest.mark.asyncio
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
