"""
Phase 6 单元测试 —— 会员域模型/Schema/路由

运行: cd backend && uv run pytest tests/unit/test_commerce_phase6.py -v
"""

from __future__ import annotations

import uuid


class TestMemberModels:
    def test_address_tablename(self):
        from app.models.member.member import UmsMemberAddress

        assert UmsMemberAddress.__tablename__ == "ums_member_addresses"

    def test_favorite_tablename(self):
        from app.models.member.member import UmsMemberFavorite

        assert UmsMemberFavorite.__tablename__ == "ums_member_favorites"


class TestMemberSchemas:
    def test_address_create(self):
        from app.schemas.member import AddressCreate

        a = AddressCreate(name="张三", phone="13800138000", detail_address="北京市朝阳区")
        assert a.default_status == 0

    def test_address_update_partial(self):
        from app.schemas.member import AddressUpdate

        u = AddressUpdate(default_status=1)
        assert u.model_dump(exclude_unset=True) == {"default_status": 1}

    def test_favorite_response(self):
        from app.schemas.member import FavoriteResponse

        f = FavoriteResponse(id=uuid.uuid4(), product_id=uuid.uuid4(), product_name="Test")
        assert f.product_name == "Test"

    def test_member_profile(self):
        from app.schemas.member import MemberProfileResponse

        m = MemberProfileResponse(id=uuid.uuid4(), email="test@test.com", is_active=True)
        assert m.email == "test@test.com"


class TestRoutes:
    def test_admin_members(self):
        from app.api.admin import admin_router

        paths = [r.path for r in admin_router.routes]
        assert any("/admin/members" in p for p in paths)

    def test_portal_member(self):
        from app.api.portal import portal_router

        paths = [r.path for r in portal_router.routes]
        assert any("/portal/member/profile" in p for p in paths)
        assert any("/portal/member/addresses" in p for p in paths)
        assert any("/portal/member/favorites" in p for p in paths)


class TestMigration:
    def test_exists(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "p6",
            "alembic/versions/f6a7b8c9d0e1_create_commerce_member_tables.py",
        )
        assert spec is not None

    def test_chain(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "p6",
            "alembic/versions/f6a7b8c9d0e1_create_commerce_member_tables.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert mod.revision == "f6a7b8c9d0e1"
        assert mod.down_revision == "e5f6a7b8c9d0"
