import unittest
import tkinter as tk
from ui.components.tag_form import TagFormFrame, READ_COMMANDS

class DummyReader:
    def __init__(self):
        self._connected = True
        self.written_bytes = []

    def is_connected(self):
        return self._connected

    def write_bytes(self, data: bytes):
        self.written_bytes.append(data)

class DummyLogConsole:
    def append(self, text):
        pass
    def append_log(self, text):
        pass
    def append_json(self, **kwargs):
        pass

class TestReadAllRetry(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.reader = DummyReader()
        self.tag_form = TagFormFrame(
            parent_frame=self.root,
            root=self.root,
            reader=self.reader,
            log_console_getter=lambda: DummyLogConsole()
        )

    def tearDown(self):
        self.tag_form.clear_pending_requests()
        self.root.destroy()

    def test_read_all_retry_on_failure(self):
        import time
        self.tag_form.read_all_fields()
        # First command sent (tag_id)
        self.assertEqual(len(self.reader.written_bytes), 1)
        first_cmd_bytes = bytes.fromhex(READ_COMMANDS["tag_id"][0])
        self.assertEqual(self.reader.written_bytes[0], first_cmd_bytes)

        # Trigger failure on first attempt
        self.assertIn(0x00, self.tag_form.pending_requests)
        self.tag_form.pending_requests[0x00]["on_failure"]("NACK")

        # Process pending timer events after 250ms delay
        time.sleep(0.3)
        self.root.update()
        self.assertEqual(len(self.reader.written_bytes), 2)
        self.assertEqual(self.reader.written_bytes[1], first_cmd_bytes)

    def test_read_all_advances_to_next_after_max_retries(self):
        import time
        self.tag_form.read_all_fields()
        # Attempt 1 (tag_id)
        self.assertEqual(len(self.reader.written_bytes), 1)
        self.tag_form.pending_requests[0x00]["on_failure"]("NACK")
        time.sleep(0.3)
        self.root.update()

        # Attempt 2 (tag_id retry 1)
        self.assertEqual(len(self.reader.written_bytes), 2)
        self.tag_form.pending_requests[0x00]["on_failure"]("NACK")
        time.sleep(0.3)
        self.root.update()

        # Attempt 3 (tag_id retry 2)
        self.assertEqual(len(self.reader.written_bytes), 3)
        self.tag_form.pending_requests[0x00]["on_failure"]("NACK")
        time.sleep(0.6)  # delay_between_fields_ms
        self.root.update()

        # Should now have moved to next parameter (serial)
        self.assertEqual(len(self.reader.written_bytes), 4)
        serial_cmd_bytes = bytes.fromhex(READ_COMMANDS["serial"][0])
        self.assertEqual(self.reader.written_bytes[3], serial_cmd_bytes)

    def test_read_all_advances_to_next_after_max_retries_zero_tag(self):
        import time
        self.tag_form.read_all_fields()
        # Attempt 1 (tag_id)
        self.assertEqual(len(self.reader.written_bytes), 1)
        self.tag_form.pending_requests[0x00]["on_success"]("000000000000000000000000")
        time.sleep(0.3)
        self.root.update()

        # Attempt 2 (tag_id retry 1)
        self.assertEqual(len(self.reader.written_bytes), 2)
        self.tag_form.pending_requests[0x00]["on_success"]("000000000000000000000000")
        time.sleep(0.3)
        self.root.update()

        # Attempt 3 (tag_id retry 2)
        self.assertEqual(len(self.reader.written_bytes), 3)
        self.tag_form.pending_requests[0x00]["on_success"]("000000000000000000000000")
        time.sleep(0.6)  # delay_between_fields_ms
        self.root.update()

        # Should now have moved to next parameter (serial)
        self.assertEqual(len(self.reader.written_bytes), 4)
        serial_cmd_bytes = bytes.fromhex(READ_COMMANDS["serial"][0])
        self.assertEqual(self.reader.written_bytes[3], serial_cmd_bytes)

    def test_write_field_retry_on_negative_response(self):
        import time
        self.tag_form.set_field_value("axle", "3")
        self.tag_form.write_field("axle")

        # Initial write transmission (param_id = 0x03)
        self.assertEqual(len(self.reader.written_bytes), 1)
        self.assertIn(0x03, self.tag_form.pending_requests)

        # Trigger Negative Response failure callback (as ui/app.py does by popping request)
        cb = self.tag_form.pending_requests.pop(0x03)["on_failure"]
        cb("NACK")
        time.sleep(0.3)
        self.root.update()

        # Should have sent retry attempt 1
        self.assertEqual(len(self.reader.written_bytes), 2)
        self.assertIn(0x03, self.tag_form.pending_requests)

    def test_write_field_ends_after_max_retries(self):
        import time
        self.tag_form.set_field_value("axle", "3")
        self.tag_form.write_field("axle")

        # Attempt 1
        self.assertEqual(len(self.reader.written_bytes), 1)
        cb = self.tag_form.pending_requests.pop(0x03)["on_failure"]
        cb("NACK")
        time.sleep(0.3)
        self.root.update()

        # Attempt 2 (retry 1)
        self.assertEqual(len(self.reader.written_bytes), 2)
        cb = self.tag_form.pending_requests.pop(0x03)["on_failure"]
        cb("NACK")
        time.sleep(0.3)
        self.root.update()

        # Attempt 3 (retry 2)
        self.assertEqual(len(self.reader.written_bytes), 3)
        cb = self.tag_form.pending_requests.pop(0x03)["on_failure"]
        cb("NACK")
        time.sleep(0.3)
        self.root.update()

    def test_read_all_sequence_stops_at_gvw_and_skips_cert(self):
        import time
        self.tag_form.read_all_fields()

        # Iterate through all 6 fields in READ_ALL_FIELDS
        expected_params = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05]
        for idx, param in enumerate(expected_params):
            self.assertEqual(len(self.reader.written_bytes), idx + 1)
            self.assertIn(param, self.tag_form.pending_requests)
            # Send positive response for this field
            cb = self.tag_form.pending_requests.pop(param)["on_success"]
            cb("TEST_VAL" if param != 0x00 else "E28068900000000000000001")
            time.sleep(0.6)
            self.root.update()

        # Sequence should be completed after GVW (0x05) without requesting TA Certification (0x06)
        self.assertEqual(len(self.reader.written_bytes), 6)
        self.assertFalse(self.tag_form._read_all_active)
        self.assertNotIn(0x06, self.tag_form.pending_requests)

    def test_individual_read_cert_still_works(self):
        self.tag_form.read_field("cert")
        self.assertEqual(len(self.reader.written_bytes), 1)
        cert_cmd_bytes = bytes.fromhex(READ_COMMANDS["cert"][0])
        self.assertEqual(self.reader.written_bytes[0], cert_cmd_bytes)
        self.assertIn(0x06, self.tag_form.pending_requests)

if __name__ == "__main__":
    unittest.main()
