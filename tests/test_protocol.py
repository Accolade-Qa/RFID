"""Unit tests for protocol framing, field specs, and SET command frame builder."""

import pytest
from communication.protocol import (
    FIELD_SPECS,
    HEADER,
    TRAILER,
    ECU_ID_VLDT,
    SET_CMD_ID,
    build_write_transmission_frame,
)
from communication.crc import aepl_rfid_calculate_crc16, crc_to_bytes


class TestProtocol:
    def test_field_specs_completeness(self):
        expected_fields = ["serial", "vin", "axle", "registration", "gvw", "cert", "rel_version"]
        for field in expected_fields:
            assert field in FIELD_SPECS
            spec = FIELD_SPECS[field]
            assert "field_id" in spec
            assert "dtype" in spec
            assert "data_len" in spec
            assert "conversion" in spec
            assert "name" in spec

    def test_build_write_frame_serial_positive(self):
        frame, frame_hex, metadata = build_write_transmission_frame("serial", "SERIAL1234567890")
        assert frame[0] == HEADER  # 0x24 ($)
        assert frame[1] == ECU_ID_VLDT  # 0x11
        assert frame[3] == SET_CMD_ID  # 0x29
        assert frame[4] == 0x01  # Param ID for Serial
        assert frame[-1] == TRAILER  # 0x23 (#)
        assert metadata["Name"] == "Serial Reader Number"
        assert metadata["Operation"] == "Write"

    def test_build_write_frame_vin_positive(self):
        frame, frame_hex, metadata = build_write_transmission_frame("vin", "MA3EVA1234VLTD01")
        assert frame[0] == HEADER
        assert frame[1] == ECU_ID_VLDT
        assert frame[3] == SET_CMD_ID
        assert frame[4] == 0x02  # Param ID for VIN
        assert frame[-1] == TRAILER
        assert metadata["Field_ID"] == "0x02"

    def test_build_write_frame_axle_positive(self):
        frame, frame_hex, metadata = build_write_transmission_frame("axle", "3")
        assert frame[4] == 0x03  # Param ID for Axle
        payload = frame[5:7]  # uint16 (2 bytes)
        assert int.from_bytes(payload, "big") == 3

    def test_build_write_frame_registration_positive(self):
        frame, frame_hex, metadata = build_write_transmission_frame("registration", "MH12AB1234")
        assert frame[4] == 0x04  # Param ID for Reg
        assert metadata["Conversion"] == "alphanumeric"

    def test_build_write_frame_gvw_decimal_positive(self):
        frame, frame_hex, metadata = build_write_transmission_frame("gvw", "45000")
        assert frame[4] == 0x05  # Param ID for GVW
        payload = frame[5:9]  # uint32 (4 bytes)
        assert int.from_bytes(payload, "big") == 45000

    def test_build_write_frame_cert_hex_positive(self):
        frame, frame_hex, metadata = build_write_transmission_frame("cert", "12 34")
        assert frame[4] == 0x06  # Param ID for Cert
        payload = frame[5:7]  # 2 bytes
        assert payload == b"\x12\x34"

    def test_build_write_frame_rel_version_positive(self):
        frame, frame_hex, metadata = build_write_transmission_frame("rel_version", "1.0.0_REL18_R")
        assert frame[4] == 0x07  # Param ID for Rel Version
        assert metadata["Name"] == "Release Version"

    def test_build_write_frame_unknown_field_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown field name"):
            build_write_transmission_frame("invalid_field", "value")

    def test_build_write_frame_string_truncation_edge_case(self):
        # VIN spec max length is 17 chars
        long_vin = "12345678901234567890EXTRA"
        frame, frame_hex, metadata = build_write_transmission_frame("vin", long_vin)
        payload = frame[5:22]
        assert len(payload) == 17
        assert payload == b"12345678901234567"

    def test_build_write_frame_string_padding_edge_case(self):
        short_vin = "SHORTVIN"
        frame, frame_hex, metadata = build_write_transmission_frame("vin", short_vin)
        payload = frame[5:22]
        assert len(payload) == 17
        assert payload.startswith(b"SHORTVIN")
        assert payload[8:] == b" " * 9

    def test_build_write_frame_invalid_hex_fallback(self):
        # Passing invalid hex string to hex field
        frame, frame_hex, metadata = build_write_transmission_frame("cert", "INVALID_HEX_ZZ")
        payload = frame[5:7]
        assert payload == b"\x00\x00"

    def test_build_write_frame_invalid_numeric_fallback(self):
        # Passing letters to axle numeric field
        frame, frame_hex, metadata = build_write_transmission_frame("axle", "NOT_A_NUMBER")
        payload = frame[5:7]
        assert int.from_bytes(payload, "big") == 0

    def test_build_write_frame_crc_verifiable(self):
        frame, frame_hex, metadata = build_write_transmission_frame("axle", "2")
        # Extract body before CRC: index 0 to -3
        body_before_crc = frame[:-3]
        crc_in_frame = frame[-3:-1]
        calc_crc = aepl_rfid_calculate_crc16(body_before_crc, len(body_before_crc))
        assert crc_to_bytes(calc_crc, big_endian=True) == crc_in_frame
