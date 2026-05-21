"""认证安全函数单元测试。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import pytest
from jose import jwt

from shared.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "my-secure-password-123"
        h = hash_password(pw)
        assert verify_password(pw, h)
        assert not verify_password("wrong", h)
        assert not verify_password("", h)
        assert h != pw

    def test_different_salts(self):
        pw = "test123456"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2
        assert verify_password(pw, h1)
        assert verify_password(pw, h2)


class TestJWT:
    def test_create_and_verify(self):
        token = create_access_token({"sub": "user-123"})
        payload = verify_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_expired_token(self):
        from datetime import timedelta
        token = create_access_token({"sub": "x"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(Exception):
            verify_token(token)

    def test_invalid_token(self):
        with pytest.raises(Exception):
            verify_token("invalid.token.here")

    def test_wrong_secret(self):
        token = jwt.encode({"sub": "x"}, "wrong-secret", algorithm="HS256")
        with pytest.raises(Exception):
            verify_token(token)
