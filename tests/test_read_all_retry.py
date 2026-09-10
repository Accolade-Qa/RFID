import unittest
from unittest.mock import MagicMock, call
from ui.components.tag_form import TagFormFrame, READ_COMMANDS


class TestReadAllRetryLogic(unittest.TestCase):
    def setUp(self):
        # Create TagFormFrame instance with mocked root, reader, and callbacks
        self.root = MagicMock()
        self.parent = MagicMock()
        self.reader = MagicMock()
        self.reader.is_connected.return_value = True
        self.log_console = MagicMock()

        # Mock timers map to simulate root.after and root.after_cancel
        self.scheduled_callbacks = {}
        self.timer_id_counter = 0

        def mock_after(ms, callback=None):
            self.timer_id_counter += 1
            tid = f"timer_{self.timer_id_counter}"
            self.scheduled_callbacks[tid] = (ms, callback)
            return tid

        def mock_after_cancel(tid):
            if tid in self.scheduled_callbacks:
                del self.scheduled_callbacks[tid]

        self.root.after = mock_after
        self.root.after_cancel = mock_after_cancel

        self.form = TagFormFrame.__new__(TagFormFrame)
        self.form.root = self.root
        self.form.reader = self.reader
        self.form.get_log_console = lambda: self.log_console
        self.form.reset_reader_status_cb = None
        self.form.timeout_cb = None
        self.form.field_vars = {}
        self.form.entry_widgets = {}
        self.form.pending_requests = {}
        self.form.request_counter = 0
        self.form.read_all_active = False
        self.form.read_all_commands = []
        self.form.read_all_index = 0
        self.form.read_all_retries = 0
        self.form.read_all_timer_id = None
        self.form.single_read_retries = {}

    def trigger_timer(self, tid):
        """Helper to fire a scheduled timer callback."""
        if tid in self.scheduled_callbacks:
            ms, callback = self.scheduled_callbacks.pop(tid)
            if callback:
                callback()

    def test_read_all_negative_response_two_retries_then_next(self):
        """
        Verify that during Read All, a negative response triggers up to 2 retries
        spaced 250ms apart, and then advances to the next parameter.
        """
        self.form.read_all_fields()
        self.assertTrue(self.form.read_all_active)
        self.assertEqual(self.form.read_all_index, 0)
        self.assertEqual(self.form.read_all_retries, 0)

        # First command sent (Tag ID, param_id 0x00)
        tag_id_cmd_bytes = bytes.fromhex(READ_COMMANDS["tag_id"][0])
        self.reader.write_bytes.assert_called_with(tag_id_cmd_bytes)
        self.assertEqual(self.reader.write_bytes.call_count, 1)

        # 1. First Negative Response received for Tag ID (0x00)
        self.form.handle_negative_response(failed_cmd=0x00, error_code=0x01)
        self.assertEqual(self.form.read_all_retries, 1)
        self.assertEqual(self.form.read_all_index, 0)

        # Verify timer scheduled for 250ms retry
        retry1_timer_id = self.form.read_all_timer_id
        self.assertIsNotNone(retry1_timer_id)
        self.assertEqual(self.scheduled_callbacks[retry1_timer_id][0], 250)

        # Trigger 250ms retry 1
        self.trigger_timer(retry1_timer_id)
        self.assertEqual(self.reader.write_bytes.call_count, 2)

        # 2. Second Negative Response received for Tag ID (0x00)
        self.form.handle_negative_response(failed_cmd=0x00, error_code=0x01)
        self.assertEqual(self.form.read_all_retries, 2)
        self.assertEqual(self.form.read_all_index, 0)

        # Verify timer scheduled for 250ms retry 2
        retry2_timer_id = self.form.read_all_timer_id
        self.assertIsNotNone(retry2_timer_id)
        self.assertEqual(self.scheduled_callbacks[retry2_timer_id][0], 250)

        # Trigger 250ms retry 2
        self.trigger_timer(retry2_timer_id)
        self.assertEqual(self.reader.write_bytes.call_count, 3)

        # 3. Third Negative Response received for Tag ID (0x00) (failed after 2 retries)
        self.form.handle_negative_response(failed_cmd=0x00, error_code=0x01)
        # Should move to next parameter (index 1 = Serial Number) and reset retries
        self.assertEqual(self.form.read_all_index, 1)
        self.assertEqual(self.form.read_all_retries, 0)

        # Trigger next parameter dispatch
        next_timer_id = self.form.read_all_timer_id
        self.assertIsNotNone(next_timer_id)
        self.trigger_timer(next_timer_id)

        # Now Serial Number (param_id 0x01) should be transmitted
        serial_cmd_bytes = bytes.fromhex(READ_COMMANDS["serial"][0])
        self.assertEqual(self.reader.write_bytes.call_args[0][0], serial_cmd_bytes)

    def test_read_all_success_on_retry(self):
        """
        Verify that if a parameter returns negative response once and succeeds on retry 1,
        it advances to the next parameter.
        """
        self.form.read_all_fields()
        self.assertEqual(self.form.read_all_index, 0)

        # 1. Negative response
        self.form.handle_negative_response(failed_cmd=0x00, error_code=0x01)
        self.assertEqual(self.form.read_all_retries, 1)
        retry_timer_id = self.form.read_all_timer_id
        self.trigger_timer(retry_timer_id)

        # 2. Positive response arrives on retry with valid Tag ID
        self.form.handle_positive_response(param_id=0x00, decoded_val="E28068200000000000000001")
        self.assertEqual(self.form.read_all_index, 1)
        self.assertEqual(self.form.read_all_retries, 0)

    def test_read_all_zero_tag_id_retries_two_times_then_next(self):
        """
        Verify that during Read All, if Tag ID returns all zeros ('000000000000000000000000'),
        it retries up to 2 times at 250ms and then advances to next parameter.
        """
        self.form.read_all_fields()
        self.assertEqual(self.form.read_all_index, 0)
        self.assertEqual(self.form.read_all_retries, 0)

        # 1. First response is all zeros
        self.form.handle_positive_response(param_id=0x00, decoded_val="000000000000000000000000")
        self.assertEqual(self.form.read_all_retries, 1)
        self.assertEqual(self.form.read_all_index, 0)

        # Verify retry timer at 250ms
        retry1_timer_id = self.form.read_all_timer_id
        self.assertIsNotNone(retry1_timer_id)
        self.assertEqual(self.scheduled_callbacks[retry1_timer_id][0], 250)
        self.trigger_timer(retry1_timer_id)

        # 2. Second response is all zeros
        self.form.handle_positive_response(param_id=0x00, decoded_val="000000000000000000000000")
        self.assertEqual(self.form.read_all_retries, 2)
        self.assertEqual(self.form.read_all_index, 0)

        retry2_timer_id = self.form.read_all_timer_id
        self.assertIsNotNone(retry2_timer_id)
        self.assertEqual(self.scheduled_callbacks[retry2_timer_id][0], 250)
        self.trigger_timer(retry2_timer_id)

        # 3. Third response is all zeros (exhausted 2 retries)
        self.form.handle_positive_response(param_id=0x00, decoded_val="000000000000000000000000")
        # Should advance to next parameter (index 1 = Serial Number)
        self.assertEqual(self.form.read_all_index, 1)
        self.assertEqual(self.form.read_all_retries, 0)

    def test_read_all_zero_tag_id_succeeds_on_retry(self):
        """
        Verify that if Tag ID returns all zeros on first attempt but returns valid alphanumeric
        Tag ID on retry 1, it advances to next parameter normally.
        """
        self.form.read_all_fields()
        self.assertEqual(self.form.read_all_index, 0)

        # 1. First response is all zeros
        self.form.handle_positive_response(param_id=0x00, decoded_val="000000000000000000000000")
        self.assertEqual(self.form.read_all_retries, 1)
        retry_timer_id = self.form.read_all_timer_id
        self.trigger_timer(retry_timer_id)

        # 2. Second response is valid Tag ID
        self.form.handle_positive_response(param_id=0x00, decoded_val="E28068200000000000000001")
        self.assertEqual(self.form.read_all_index, 1)
        self.assertEqual(self.form.read_all_retries, 0)

    def test_single_read_zero_tag_id_retries(self):
        """
        Verify that single Read Tag ID button retries up to 2 times when returning all zeros.
        """
        self.form.read_field("tag_id")
        self.assertFalse(self.form.read_all_active)
        self.assertEqual(self.reader.write_bytes.call_count, 1)

        # 1. Response is all zeros -> triggers retry 1
        self.form.handle_positive_response(param_id=0x00, decoded_val="000000000000000000000000")
        self.assertEqual(self.form.single_read_retries[0x00], 1)

        # 2. Second response is valid Tag ID -> no more retries
        self.form.handle_positive_response(param_id=0x00, decoded_val="E28068200000000000000001")
        self.assertEqual(self.form.single_read_retries[0x00], 1)


if __name__ == "__main__":
    unittest.main()
