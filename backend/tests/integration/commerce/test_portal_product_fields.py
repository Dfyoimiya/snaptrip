"""
Integration tests: Portal product endpoints must not leak internal admin fields.

Internal status fields (publish_status, verify_status, preview_status) are
meant for the admin interface only. The portal (public-facing) endpoints
should return a sanitized response that omits these fields.

NOTE: The current ProductResponse / ProductDetailResponse schemas DO include
these fields, so these tests will initially fail. Once a dedicated portal
product response schema strips them out, these tests validate the fix.

Author: SnapTrip QA Team
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

INTERNAL_STATUS_FIELDS = {"publish_status", "verify_status", "preview_status"}


class TestPortalProductFields:
    """Admin-only fields must not appear in portal product responses."""

    @pytest_asyncio.fixture
    async def setup_verified_product(self, auth_client: AsyncClient) -> dict:
        """
        Create a product via admin API, verify it so it becomes visible
        on the portal. Returns product_id and product_name.
        """
        # ---- 1. Prepare category + brand ----
        cat_resp = await auth_client.post("/api/v1/admin/categories", json={"name": "门户字段测试分类"})
        cat_id = cat_resp.json()["data"]["id"]

        brand_resp = await auth_client.post("/api/v1/admin/brands", json={"name": "PortalFields"})
        brand_id = brand_resp.json()["data"]["id"]

        # ---- 2. Create product ----
        prod_resp = await auth_client.post(
            "/api/v1/admin/products",
            json={
                "name": "门户字段测试商品",
                "price": "299.00",
                "category_id": cat_id,
                "brand_id": brand_id,
                "publish_status": 1,
                "skus": [
                    {
                        "sku_code": "PF-001",
                        "spec": '{"color":"黑色"}',
                        "price": "299.00",
                        "stock": 100,
                    }
                ],
            },
        )
        product_id = prod_resp.json()["data"]["id"]
        product_name = prod_resp.json()["data"]["name"]

        # ---- 3. Verify (approve) so it's portal-visible ----
        await auth_client.patch(f"/api/v1/admin/products/{product_id}/verify?status=1")

        return {"product_id": product_id, "product_name": product_name}

    # ------------------------------------------------------------------
    #  Single product detail
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_portal_detail_excludes_internal_status_fields(
        self, public_client: AsyncClient, setup_verified_product: dict
    ):
        """GET /portal/products/{id} response should NOT contain internal status fields."""
        product_id = setup_verified_product["product_id"]
        resp = await public_client.get(f"/api/v1/portal/products/{product_id}")
        assert resp.status_code == 200, resp.text

        data = resp.json()["data"]
        response_fields = set(data.keys())

        # Assert internal admin-only fields are NOT leaked to portal
        leaked = INTERNAL_STATUS_FIELDS & response_fields
        assert not leaked, f"Portal product detail leaked internal fields: {leaked}. Fields present: {response_fields}"

    @pytest.mark.asyncio
    async def test_portal_detail_contains_public_fields(self, public_client: AsyncClient, setup_verified_product: dict):
        """GET /portal/products/{id} should include expected public fields (name, price, etc.)."""
        product_id = setup_verified_product["product_id"]
        resp = await public_client.get(f"/api/v1/portal/products/{product_id}")
        assert resp.status_code == 200, resp.text

        data = resp.json()["data"]
        assert data["name"] == setup_verified_product["product_name"]
        assert "price" in data
        assert "skus" in data
        assert len(data["skus"]) >= 1
        assert data["skus"][0]["sku_code"] == "PF-001"

    # ------------------------------------------------------------------
    #  Product list
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_portal_list_excludes_internal_status_fields(
        self, public_client: AsyncClient, setup_verified_product: dict
    ):
        """GET /portal/products list items should NOT contain internal status fields."""
        # Search by the product name so we get at least one result
        resp = await public_client.get(
            "/api/v1/portal/products",
            params={"keyword": "门户字段测试商品"},
        )
        assert resp.status_code == 200, resp.text

        items = resp.json()["data"]["items"]
        assert len(items) >= 1, "Expected at least one product in portal list"

        for item in items:
            response_fields = set(item.keys())
            leaked = INTERNAL_STATUS_FIELDS & response_fields
            assert not leaked, (
                f"Portal product list item leaked internal fields: {leaked}. Fields present: {response_fields}"
            )

    @pytest.mark.asyncio
    async def test_portal_list_contains_public_fields(self, public_client: AsyncClient, setup_verified_product: dict):
        """GET /portal/products list items should include expected public fields."""
        resp = await public_client.get("/api/v1/portal/products", params={"page": 1, "page_size": 10})
        assert resp.status_code == 200, resp.text

        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

        for item in data["items"]:
            # Required public-facing fields
            assert "id" in item
            assert "name" in item
            assert "price" in item

    # ------------------------------------------------------------------
    #  Category browse
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_portal_category_browse_excludes_internal_fields(
        self, public_client: AsyncClient, setup_verified_product: dict
    ):
        """GET /portal/products/category/{id} items should NOT contain internal status fields."""
        # Get the category used by the setup product
        # First get the product detail to find the category_id
        product_id = setup_verified_product["product_id"]
        detail = await public_client.get(f"/api/v1/portal/products/{product_id}")
        category_id = detail.json()["data"].get("category_id")

        if not category_id:
            pytest.skip("No category_id on product — category browse not testable")

        resp = await public_client.get(
            f"/api/v1/portal/products/category/{category_id}",
            params={"page": 1, "page_size": 10},
        )
        assert resp.status_code == 200, resp.text

        for item in resp.json()["data"]["items"]:
            response_fields = set(item.keys())
            leaked = INTERNAL_STATUS_FIELDS & response_fields
            assert not leaked, f"Category browse item leaked internal fields: {leaked}"
