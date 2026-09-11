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

if __name__ == "__main__":
    unittest.main()
