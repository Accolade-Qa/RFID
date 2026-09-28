"""Validation functions for RFID UI field entries."""

import re


REL_VERSION_PLACEHOLDER = "1.0.0_REL18_R"
TAG_ID_PLACEHOLDER = "(Alphanumeric: Max 24 Characters)"
SERIAL_PLACEHOLDER = "(Alphanumeric: Max 16 characters)"
VIN_PLACEHOLDER = "(Alphanumeric: Max 17 Characters)"
AXLE_PLACEHOLDER = "(Numeric: 0 to 65535)"
GVW_PLACEHOLDER = "(Decimal: e.g. 45000.50)"
REGISTRATION_PLACEHOLDER = "(Alphanumeric: Max 12 Characters)"


def normalize_rel_version_value(value: str) -> str:
    cleaned = (value or "").strip()
    # want to add 2 digit version number
    if cleaned.startswith(re.compile("18")) and cleaned[3:4] == ".":
        return cleaned[1:]
    return cleaned


def is_rel_version_valid(value: str) -> bool:
    normalized = normalize_rel_version_value(value)
    return (
        len(normalized) <= 20
        and normalized.replace(".", "").replace("-", "").replace("_", "").isalnum()
    )


def validate_rel_version_entry(new_value: str) -> bool:
    if new_value == "" or new_value == REL_VERSION_PLACEHOLDER:
        return True
    return is_rel_version_valid(new_value)


def is_tag_id_valid(value: str) -> bool:
    return len(value) <= 24 and value.isalnum()


def validate_tag_id_entry(new_value: str) -> bool:
    if new_value == "" or new_value == TAG_ID_PLACEHOLDER:
        return True
    return len(new_value) <= 24 and new_value.isalnum()


def is_serial_valid(value: str) -> bool:
    return len(value) == 16 and value.isalnum()


def validate_serial_entry(new_value: str) -> bool:
    if new_value == "" or new_value == SERIAL_PLACEHOLDER:
        return True
    return len(new_value) <= 16 and new_value.isalnum()


def is_vin_valid(value: str) -> bool:
    return len(value) == 17 and value.isalnum()


def validate_vin_entry(new_value: str) -> bool:
    if new_value == "" or new_value == VIN_PLACEHOLDER:
        return True
    return len(new_value) <= 17 and new_value.isalnum()


def is_registration_valid(value: str) -> bool:
    return len(value) == 12 and value.isalnum()


def validate_registration_entry(new_value: str) -> bool:
    if new_value == "" or new_value == REGISTRATION_PLACEHOLDER:
        return True
    return len(new_value) <= 12 and new_value.isalnum()


def is_integer_in_range(value: str, min_value: int, max_value: int) -> bool:
    if not value.isdigit():
        return False
    try:
        numeric = int(value)
        return min_value <= numeric <= max_value
    except ValueError:
        return False


def validate_numeric_range_entry(new_value: str, max_digits: str | int = 10) -> bool:
    if new_value == "" or new_value in (AXLE_PLACEHOLDER, GVW_PLACEHOLDER):
        return True
    try:
        max_d = int(max_digits)
    except (ValueError, TypeError):
        max_d = 10
    return len(new_value) <= max_d and new_value.isdigit()


def validate_gvw_decimal_entry(new_value: str, max_digits: int = 12) -> bool:
    if new_value == "" or new_value == GVW_PLACEHOLDER:
        return True
    if len(new_value) > max_digits:
        return False
    parts = new_value.split(".")
    if len(parts) > 2:
        return False
    return all(part == "" or part.isdigit() for part in parts)
