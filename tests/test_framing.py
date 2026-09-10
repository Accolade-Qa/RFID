import unittest
from unittest.mock import MagicMock
from ui.app import RFIDApp


class TestFramingLogic(unittest.TestCase):
    def setUp(self):
        # Create a mocked instance of RFIDApp without launching Tk root
        self.app = RFIDApp.__new__(RFIDApp)
        self.app.rx_buffer = bytearray()
        self.app.reader = MagicMock()
        self.app.root = MagicMock()
        self.app.comm_panel_comp = MagicMock()
        self.app.tag_form_comp = MagicMock()
        self.app.log_panel_comp = MagicMock()
        self.app.parsed_frames = []

        # Mock _parse_uart_response to record received frames
        def mock_parse(frame):
            self.app.parsed_frames.append(frame)
        self.app._parse_uart_response = mock_parse

    def test_tag_id_with_internal_0x23_bytes(self):
        """
        Verify that a Tag ID frame containing 0x23 data bytes in the middle
        is parsed strictly at expected_len where buffer[expected_len - 1] == 0x23,
        and internal 0x23 bytes are NOT treated as frame trailers.
        """
        # Full frame:
        # Header: 24 EF
        # Len: 12 (18 body bytes: tag 0x40 + 15 bytes EPC + 2 bytes CRC = 18 bytes)
        # Tag: 40
        # Payload (15 bytes) with 0x23 bytes at multiple positions:
        # E2 80 68 23 00 23 00 23 00 12 34 56 78 9A BC
        # CRC: 8E 7F
        # Trailer: 23
        payload = b"\xE2\x80\x68\x23\x00\x23\x00\x23\x00\x12\x34\x56\x78\x9A\xBC"
        body = b"\x40" + payload + b"\x8E\x7F"
        full_frame = b"\x24\xEF" + bytes([len(body)]) + body + b"\x23"

        self.assertEqual(len(full_frame), 22)  # 3 header + 18 body + 1 trailer = 22 bytes
        self.assertEqual(full_frame[2], 0x12)
        # Check that there are internal 0x23 bytes
        self.assertEqual(full_frame[7], 0x23)
        self.assertEqual(full_frame[9], 0x23)
        self.assertEqual(full_frame[11], 0x23)
        self.assertEqual(full_frame[21], 0x23)  # actual trailer

        self.app.reader.get_raw_batch.return_value = [full_frame]
        self.app.update_gui()

        self.assertEqual(len(self.app.parsed_frames), 1)
        self.assertEqual(self.app.parsed_frames[0], full_frame)
        self.assertEqual(len(self.app.rx_buffer), 0)

    def test_fragmented_reception(self):
        """Verify that fragmented incoming chunks wait until expected_len arrives."""
        payload = b"\xE2\x80\x68\x23\x00\x23\x00\x23\x00\x12\x34\x56\x78\x9A\xBC"
        body = b"\x40" + payload + b"\x8E\x7F"
        full_frame = b"\x24\xEF" + bytes([len(body)]) + body + b"\x23"

        chunk1 = full_frame[:8]   # Contains internal 0x23 at index 6
        chunk2 = full_frame[8:15]
        chunk3 = full_frame[15:]

        # Feed Chunk 1
        self.app.reader.get_raw_batch.return_value = [chunk1]
        self.app.update_gui()
        self.assertEqual(len(self.app.parsed_frames), 0)
        self.assertEqual(len(self.app.rx_buffer), 8)

        # Feed Chunk 2
        self.app.reader.get_raw_batch.return_value = [chunk2]
        self.app.update_gui()
        self.assertEqual(len(self.app.parsed_frames), 0)
        self.assertEqual(len(self.app.rx_buffer), 15)

        # Feed Chunk 3
        self.app.reader.get_raw_batch.return_value = [chunk3]
        self.app.update_gui()
        self.assertEqual(len(self.app.parsed_frames), 1)
        self.assertEqual(self.app.parsed_frames[0], full_frame)
        self.assertEqual(len(self.app.rx_buffer), 0)

    def test_garbage_leading_bytes(self):
        """Verify leading garbage bytes are discarded before valid frame."""
        frame = b"\x24\xEF\x05\x43\x00\x02\xB1\x55\x23"
        noisy_data = b"\xAA\xBB\xCC\xDD" + frame

        self.app.reader.get_raw_batch.return_value = [noisy_data]
        self.app.update_gui()

        self.assertEqual(len(self.app.parsed_frames), 1)
        self.assertEqual(self.app.parsed_frames[0], frame)
        self.assertEqual(len(self.app.rx_buffer), 0)

    def test_multiple_consecutive_frames(self):
        """Verify multiple frames received together are all parsed."""
        frame1 = b"\x24\xEF\x05\x43\x00\x02\xB1\x55\x23"
        frame2 = b"\x24\xEF\x07\x45\x00\x44\xB0\x0A\xB1\x55\x23"

        self.app.reader.get_raw_batch.return_value = [frame1 + frame2]
        self.app.update_gui()

        self.assertEqual(len(self.app.parsed_frames), 2)
        self.assertEqual(self.app.parsed_frames[0], frame1)
        self.assertEqual(self.app.parsed_frames[1], frame2)
        self.assertEqual(len(self.app.rx_buffer), 0)

    def test_direct_compact_frame(self):
        """Verify direct compact binary frame without 0x24."""
        compact_frame = b"\x04\x69\x03\x00\x14\x25\x80\x23"
        self.app.reader.get_raw_batch.return_value = [compact_frame]
        self.app.update_gui()

    def test_parse_uart_response_tag_id_with_0x23(self):
        """Verify _parse_uart_response correctly extracts full Tag ID hex containing 0x23 bytes."""
        app = RFIDApp.__new__(RFIDApp)
        app.comm_panel_comp = MagicMock()
        app.tag_form_comp = MagicMock()
        app.log_panel_comp = MagicMock()
        app.tag_form_comp.pending_requests = {
            0x00: {"Command Sent": "24 11 01 00 23", "Operation": "Read"}
        }

        # 12 payload bytes (24 hex characters) including 0x23 bytes
        payload = b"\xE2\x80\x68\x23\x00\x23\x00\x23\x00\x12\x34\x56"
        body = b"\x40" + payload + b"\x8E\x7F"
        full_frame = b"\x24\xEF" + bytes([len(body)]) + body + b"\x23"

        app._parse_uart_response(full_frame)

        expected_tag_id_hex = payload.hex().upper()
        app.tag_form_comp.set_field_value.assert_called_once_with("tag_id", expected_tag_id_hex)
        app.comm_panel_comp.show_pass.assert_called_once()


if __name__ == "__main__":
    unittest.main()
