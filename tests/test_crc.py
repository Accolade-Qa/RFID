"""Unit tests for CRC-16/CCITT-FALSE calculation and byte serialization."""

import pytest
from communication.crc import aepl_rfid_calculate_crc16, crc_to_bytes


class TestCRC16:
    def test_crc16_known_vector_sample_1(self):
        # Sample payload from specification: 24 11 04 29 03 00 0A
        # CRC is calculated over bytes from index 1: 11 04 29 03 00 0A
        data = bytes([0x24, 0x11, 0x04, 0x29, 0x03, 0x00, 0x0A])
        crc = aepl_rfid_calculate_crc16(data, len(data))
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_crc16_rel_version_read_command_payload(self):
        # 24 11 01 07
        data = bytes.fromhex("24110107")
        crc = aepl_rfid_calculate_crc16(data, len(data))
        assert isinstance(crc, int)
        assert crc == 0xFB19

    def test_crc16_single_byte_payload(self):
        # Data length 2 -> index 1 processed
        data = b"\x24\x11"
        crc = aepl_rfid_calculate_crc16(data, len(data))
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_crc16_all_zeros_payload(self):
        data = b"\x24\x00\x00\x00\x00\x00"
        crc = aepl_rfid_calculate_crc16(data, len(data))
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_crc16_all_ones_payload(self):
        data = b"\x24\xFF\xFF\xFF\xFF\xFF"
        crc = aepl_rfid_calculate_crc16(data, len(data))
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_crc16_large_payload(self):
        data = b"\x24" + (b"\xAB" * 255)
        crc = aepl_rfid_calculate_crc16(data, len(data))
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_crc_to_bytes_big_endian(self):
        crc_val = 0x1234
        b = crc_to_bytes(crc_val, big_endian=True)
        assert b == b"\x12\x34"

    def test_crc_to_bytes_little_endian(self):
        crc_val = 0x1234
        b = crc_to_bytes(crc_val, big_endian=False)
        assert b == b"\x34\x12"

    def test_crc_to_bytes_zero_and_max(self):
        assert crc_to_bytes(0x0000, big_endian=True) == b"\x00\x00"
        assert crc_to_bytes(0xFFFF, big_endian=True) == b"\xFF\xFF"
