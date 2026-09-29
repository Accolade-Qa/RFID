"""Unit tests for Threaded CANReader communicator and Virtual CAN Simulator."""

import pytest
import time
from communication.can_reader import CANReader


class TestCANReader:
    def test_can_init_defaults(self):
        reader = CANReader(channel="vcan0", bustype="virtual", bitrate=250000)
        assert reader.channel == "vcan0"
        assert reader.bitrate == 250000
        assert reader.is_connected() is False

    def test_can_connect_virtual_mode(self):
        reader = CANReader(channel="vcan0", bustype="virtual", bitrate=250000)
        success = reader.connect()
        assert success is True
        assert reader.is_connected() is True
        assert reader.is_virtual is True
        reader.disconnect()
        assert reader.is_connected() is False

    def test_can_update_can_ids_and_parameter_mapping(self):
        reader = CANReader(default_tx_id=0x7E0, default_rx_id=0x7E8)
        reader.update_can_ids(
            tx_id=0x18DAF110,
            rx_id=0x18DA10F1,
            is_extended=True,
            id_map={0x02: {"tx_id": 0x7E2, "rx_id": 0x7EA, "is_extended": False}},
        )
        assert reader.tx_id == 0x18DAF110
        assert reader.rx_id == 0x18DA10F1
        assert reader.is_extended_id is True
        assert 0x02 in reader.id_map
        assert reader.id_map[0x02]["tx_id"] == 0x7E2

    def test_can_virtual_response_read_commands(self):
        reader = CANReader(channel="vcan0", bustype="virtual")
        assert reader.connect() is True

        # Read Tag ID (0x00)
        read_tag_cmd = bytes.fromhex("241101008BFE23")
        reader.write_bytes(read_tag_cmd)
        time.sleep(0.1)

        batch = reader.get_raw_batch()
        assert len(batch) >= 1
        resp = batch[0]
        assert resp[0] == 0x24
        assert resp[3] == 0x40  # Tag ID response byte

        # Read VIN (0x02)
        read_vin_cmd = bytes.fromhex("24110102ABBC23")
        reader.write_bytes(read_vin_cmd)
        time.sleep(0.1)

        batch_vin = reader.get_raw_batch()
        assert len(batch_vin) >= 1
        assert batch_vin[0][3] == 0x42  # VIN response byte

        # Read GVW (0x05)
        read_gvw_cmd = bytes.fromhex("24110105B15523")
        reader.write_bytes(read_gvw_cmd)
        time.sleep(0.1)

        batch_gvw = reader.get_raw_batch()
        assert len(batch_gvw) >= 1
        assert batch_gvw[0][3] == 0x45  # GVW response byte

        reader.disconnect()

    def test_can_virtual_response_write_command(self):
        reader = CANReader(channel="vcan0", bustype="virtual")
        assert reader.connect() is True

        # Write Axle Count frame (param_id 0x03)
        # 24 11 04 29 03 00 02 CRC_H CRC_L 23
        write_axle_cmd = bytes.fromhex("24110429030002123423")
        reader.write_bytes(write_axle_cmd)
        time.sleep(0.1)

        batch = reader.get_raw_batch()
        assert len(batch) >= 1
        resp = batch[0]
        assert resp[0] == 0x24
        assert resp[3] == 0x43  # 0x40 + 0x03 = 0x43 (Axle Tag response)

        reader.disconnect()

    def test_can_multi_frame_reassembly(self):
        reader = CANReader(channel="vcan0", bustype="virtual")
        # Split a standard response frame across two chunk calls
        chunk1 = b"\x24\xEF\x05\x43\x00"
        chunk2 = b"\x02\xB1\x55\x23"

        reader._process_rx_can_message(chunk1)
        assert len(reader._rx_reassembly_buffer) == 5

        reader._process_rx_can_message(chunk2)
        # Should have flushed the complete frame to raw_queue
        assert len(reader._rx_reassembly_buffer) == 0
        batch = reader.get_raw_batch()
        assert len(batch) == 1
        assert batch[0] == b"\x24\xEF\x05\x43\x00\x02\xB1\x55\x23"
