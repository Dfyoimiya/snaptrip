"""
Unit tests: Phone number validation in order schemas.

Tests that the OrderCreateFromCart.receiver_phone field correctly validates
Chinese mobile phone numbers. The current schema only enforces min_length=1
and max_length=32, which is too permissive. These tests define what proper
validation should look like.

The PhoneField schema below demonstrates the regex pattern that should be
applied to receiver_phone in the production schema:
  - Must be exactly 11 digits
  - Must start with 1
  - Second digit must be 3-9 (covers all current Chinese mobile prefixes:
    13x, 14x, 15x, 16x, 17x, 18x, 19x)

Run: cd backend && uv run pytest tests/unit/test_phone_validation.py -v

Author: SnapTrip QA Team
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field, ValidationError

# ============================================================================
#  Test helper: phone-validated order schema
# ============================================================================

_CHINA_MOBILE_PATTERN = r"^1[3-9]\d{9}$"


class OrderWithPhoneValidation(BaseModel):
    """Minimal order schema with proper Chinese phone validation."""

    receiver_name: str
    receiver_phone: str = Field(
        ...,
        pattern=_CHINA_MOBILE_PATTERN,
        description="Chinese mobile phone number (11 digits, starts with 13-19)",
    )
    receiver_detail_address: str


class TestPhoneValidation:
    """Chinese mobile phone number format validation."""

    # ======================================================================
    #  Positive: valid phone numbers
    # ======================================================================

    @pytest.mark.parametrize(
        "valid_phone",
        [
            "13800138000",  # Common China Mobile (13x)
            "15912345678",  # China Unicom (15x)
            "18911111111",  # China Telecom (18x)
            "13900139000",  # China Mobile
            "15012345000",  # China Unicom
            "17012345678",  # Virtual operator (17x)
            "16612345678",  # China Unicom (16x)
            "19912345678",  # China Telecom (19x)
            "14712345678",  # China Unicom data (14x)
            "19812345678",  # China Mobile (19x)
        ],
    )
    def test_valid_chinese_phone_numbers(self, valid_phone: str):
        """Valid Chinese phone numbers pass Pydantic validation."""
        order = OrderWithPhoneValidation(
            receiver_name="张三",
            receiver_phone=valid_phone,
            receiver_detail_address="北京市朝阳区",
        )
        assert order.receiver_phone == valid_phone

    # ======================================================================
    #  Negative: invalid phone numbers
    # ======================================================================

    @pytest.mark.parametrize(
        "invalid_phone,reason",
        [
            ("12345678901", "Starts with 12, not a valid mobile prefix"),
            ("10012345678", "Starts with 10, not a valid mobile prefix"),
            ("11012345678", "Starts with 11 (emergency numbers)"),
            ("12012345678", "Starts with 12 (emergency numbers)"),
        ],
    )
    def test_invalid_phone_prefix_rejected(self, invalid_phone: str, reason: str):
        """Phone numbers with non-mobile prefixes (not 13-19) are rejected."""
        with pytest.raises(ValidationError, match="receiver_phone"):
            OrderWithPhoneValidation(
                receiver_name="张三",
                receiver_phone=invalid_phone,
                receiver_detail_address="北京市朝阳区",
            )

    @pytest.mark.parametrize(
        "invalid_phone,reason",
        [
            ("1380013800", "Only 10 digits — too short"),
            ("138001380001", "12 digits — too long"),
            ("", "Empty string"),
        ],
    )
    def test_invalid_phone_wrong_length_rejected(self, invalid_phone: str, reason: str):
        """Phone numbers with incorrect length (not 11 digits) are rejected."""
        with pytest.raises(ValidationError, match="receiver_phone"):
            OrderWithPhoneValidation(
                receiver_name="张三",
                receiver_phone=invalid_phone,
                receiver_detail_address="北京市朝阳区",
            )

    @pytest.mark.parametrize(
        "invalid_phone,reason",
        [
            ("13800a38000", "Contains letter 'a'"),
            ("13800 38000", "Contains space"),
            ("13800-38000", "Contains hyphen"),
            ("１３８００１３８０００", "Fullwidth digits (Unicode)"),
            ("+8613800138000", "Contains country code prefix"),
        ],
    )
    def test_invalid_phone_non_digit_characters_rejected(self, invalid_phone: str, reason: str):
        """Phone numbers containing non-digit characters are rejected."""
        with pytest.raises(ValidationError, match="receiver_phone"):
            OrderWithPhoneValidation(
                receiver_name="张三",
                receiver_phone=invalid_phone,
                receiver_detail_address="北京市朝阳区",
            )

    @pytest.mark.parametrize(
        "invalid_phone,reason",
        [
            ("12345678901", "Second digit is 2, not in 3-9 range"),
            ("11111111111", "Second digit is 1"),
            ("10000000000", "Second digit is 0"),
        ],
    )
    def test_invalid_phone_second_digit_range_rejected(self, invalid_phone: str, reason: str):
        """Phone numbers where the second digit is outside 3-9 are rejected."""
        with pytest.raises(ValidationError, match="receiver_phone"):
            OrderWithPhoneValidation(
                receiver_name="张三",
                receiver_phone=invalid_phone,
                receiver_detail_address="北京市朝阳区",
            )

    # ======================================================================
    #  Current schema behavior: the production OrderCreateFromCart schema
    #  is too permissive. These tests document the gap.
    # ======================================================================

    def test_production_schema_rejects_invalid_phone(self):
        """
        Production OrderCreateFromCart now enforces Chinese phone format via regex.
        Invalid phones are rejected with ValidationError.
        """
        import uuid

        from pydantic import ValidationError

        from app.schemas.order import OrderCreateFromCart

        with pytest.raises(ValidationError, match="receiver_phone"):
            OrderCreateFromCart(
                cart_item_ids=[uuid.uuid4()],
                receiver_name="张三",
                receiver_phone="12345",
                receiver_detail_address="北京市朝阳区",
            )
