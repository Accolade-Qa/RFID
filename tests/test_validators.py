"""Unit tests for UI field input validators, placeholders, and range checks."""

import pytest
from validation.validators import (
    REL_VERSION_PLACEHOLDER,
    TAG_ID_PLACEHOLDER,
    SERIAL_PLACEHOLDER,
    VIN_PLACEHOLDER,
    AXLE_PLACEHOLDER,
    GVW_PLACEHOLDER,
    REGISTRATION_PLACEHOLDER,
    normalize_rel_version_value,
    is_rel_version_valid,
    validate_rel_version_entry,
    is_tag_id_valid,
    validate_tag_id_entry,
    is_serial_valid,
    validate_serial_entry,
    is_vin_valid,
    validate_vin_entry,
    is_registration_valid,
    validate_registration_entry,
    is_integer_in_range,
    validate_numeric_range_entry,
    validate_gvw_decimal_entry,
)


class TestValidators:
    # -------------------------------------------------------------
    # Release Version
    # -------------------------------------------------------------
    def test_normalize_rel_version_value_strips_leading_8(self):
        assert normalize_rel_version_value("818.2.0_REL02_R") == "18.2.0_REL02_R"
        assert normalize_rel_version_value("1.0.0_REL18_R") == "1.0.0_REL18_R"
        assert normalize_rel_version_value("") == ""

    def test_is_rel_version_valid(self):
        assert is_rel_version_valid("1.0.0_REL18_R") is True
        assert is_rel_version_valid("818.2.0_REL02_R") is True
        assert is_rel_version_valid("INVALID@VERSION!") is False

    def test_validate_rel_version_entry(self):
        assert validate_rel_version_entry("") is True
        assert validate_rel_version_entry(REL_VERSION_PLACEHOLDER) is True
        assert validate_rel_version_entry("1.0.0") is True
        assert validate_rel_version_entry("1.0.0_INVALID#$") is False

    # -------------------------------------------------------------
    # Tag EPC ID
    # -------------------------------------------------------------
    def test_tag_id_validation(self):
        assert is_tag_id_valid("E28068900000000000000001") is True  # 24 chars
        assert is_tag_id_valid("E280689000000000000000001") is False  # 25 chars (too long)
        assert is_tag_id_valid("E2806890-000") is False  # special chars

        assert validate_tag_id_entry("") is True
        assert validate_tag_id_entry(TAG_ID_PLACEHOLDER) is True
        assert validate_tag_id_entry("ABC123") is True
        assert validate_tag_id_entry("1234567890123456789012345") is False

    # -------------------------------------------------------------
    # Serial Reader Number
    # -------------------------------------------------------------
    def test_serial_validation(self):
        assert is_serial_valid("SERIAL1234567890") is True  # 16 chars
        assert is_serial_valid("SHORT") is False  # must be 16
        assert is_serial_valid("SERIAL12345678901") is False  # 17 chars

        assert validate_serial_entry("") is True
        assert validate_serial_entry(SERIAL_PLACEHOLDER) is True
        assert validate_serial_entry("SERIAL123") is True  # Partial entry allowed while typing
        assert validate_serial_entry("SERIAL@123") is False

    # -------------------------------------------------------------
    # VIN
    # -------------------------------------------------------------
    def test_vin_validation(self):
        assert is_vin_valid("MA3EVA1234VLTD0123") is False  # 18 chars
        assert is_vin_valid("MA3EVA1234VLTD012") is True    # 17 chars

        assert validate_vin_entry("") is True
        assert validate_vin_entry(VIN_PLACEHOLDER) is True
        assert validate_vin_entry("MA3EVA123") is True
        assert validate_vin_entry("MA3EVA123!") is False

    # -------------------------------------------------------------
    # Registration Number
    # -------------------------------------------------------------
    def test_registration_validation(self):
        assert is_registration_valid("MH12AB123456") is True  # 12 chars
        assert is_registration_valid("MH12AB12345") is False  # 11 chars

        assert validate_registration_entry("") is True
        assert validate_registration_entry(REGISTRATION_PLACEHOLDER) is True
        assert validate_registration_entry("MH12") is True
        assert validate_registration_entry("MH-12-AB") is False

    # -------------------------------------------------------------
    # Numeric Range
    # -------------------------------------------------------------
    def test_integer_in_range(self):
        assert is_integer_in_range("0", 0, 65535) is True
        assert is_integer_in_range("65535", 0, 65535) is True
        assert is_integer_in_range("65536", 0, 65535) is False
        assert is_integer_in_range("-1", 0, 65535) is False
        assert is_integer_in_range("abc", 0, 65535) is False

    def test_validate_numeric_range_entry(self):
        assert validate_numeric_range_entry("") is True
        assert validate_numeric_range_entry(AXLE_PLACEHOLDER) is True
        assert validate_numeric_range_entry("123", max_digits=5) is True
        assert validate_numeric_range_entry("123456", max_digits=5) is False
        assert validate_numeric_range_entry("12a", max_digits=5) is False

    # -------------------------------------------------------------
    # GVW Decimal Entry Validation
    # -------------------------------------------------------------
    def test_gvw_decimal_validation(self):
        assert validate_gvw_decimal_entry("") is True
        assert validate_gvw_decimal_entry(GVW_PLACEHOLDER) is True
        assert validate_gvw_decimal_entry("45000") is True
        assert validate_gvw_decimal_entry("45000.50") is True
        assert validate_gvw_decimal_entry("12500.75") is True
        assert validate_gvw_decimal_entry("0.0") is True
        assert validate_gvw_decimal_entry("45000.50.10") is False  # Multiple dots
        assert validate_gvw_decimal_entry("45000a") is False  # Alphabetic
        assert validate_gvw_decimal_entry("-45000") is False  # Negative sign
        assert validate_gvw_decimal_entry("12345678901234567") is False  # Exceeds max digits
