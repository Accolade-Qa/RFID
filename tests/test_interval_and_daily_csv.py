import csv
import datetime
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from config import get_daily_csv_path
from logger.log_console import LogConsole
from ui.components.tag_form import TagFormFrame, AUTO_READ_PLACEHOLDER


class TestDailyCsvLogging(unittest.TestCase):
    def test_daily_csv_path_format(self):
        test_dt = datetime.datetime(2026, 9, 7, 10, 30, 0)
        daily_path = get_daily_csv_path(test_dt)
        self.assertTrue(daily_path.endswith("activity_records_2026-09-07.csv"))

    def test_append_csv_auto_creates_daily_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_dt = datetime.datetime(2026, 9, 8, 12, 0, 0)
            custom_daily_path = os.path.join(tmp_dir, f"activity_records_{test_dt.strftime('%Y-%m-%d')}.csv")

            log_console = LogConsole()
            log_console.set_csv_file_path(custom_daily_path)

            success = log_console.append_csv(
                name="Tag ID",
                operation="Read",
                command_sent="24110100E1F023",
                response_received="E2004704CB506021A9450113",
                conversion="hex as it is",
                medium="UART",
            )
            self.assertTrue(success)
            self.assertTrue(os.path.exists(custom_daily_path))

            with open(custom_daily_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["Name"], "Tag ID")
                self.assertEqual(rows[0]["Operation"], "Read")
                self.assertEqual(rows[0]["Command Sent"], "24110100E1F023")
                self.assertEqual(rows[0]["Response Received"], "E2004704CB506021A9450113")
                self.assertEqual(rows[0]["Conversion"], "hex as it is")
                self.assertEqual(rows[0]["Medium of transmission"], "UART")
                self.assertTrue(rows[0]["Date and Time"] != "")


class TestIntervalStopOnRead(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.root = tk.Tk()
        self.root.withdraw()

        self.mock_reader = MagicMock()
        self.mock_reader.is_connected.return_value = True
        self.mock_reader.write_bytes = MagicMock()

        self.mock_log_console = MagicMock()

        self.parent = tk.Frame(self.root)
        self.parent.pack()

        self.tag_form = TagFormFrame(
            parent_frame=self.parent,
            root=self.root,
            reader=self.mock_reader,
            log_console_getter=lambda: self.mock_log_console,
        )

    def tearDown(self):
        try:
            self.tag_form._stop_all_auto_reads()
            self.root.destroy()
        except Exception:
            pass

    def test_interval_starts_when_value_provided(self):
        self.tag_form.interval_vars["tag_id"].set("2")
        self.tag_form.read_field("tag_id")

        self.assertTrue(self.tag_form.auto_read_active.get("tag_id"))
        self.assertEqual(self.tag_form.auto_read_intervals.get("tag_id"), 2)
        self.assertIn("tag_id", self.tag_form.auto_read_jobs)

    def test_interval_stops_when_value_removed_and_read_clicked(self):
        # 1. Start interval
        self.tag_form.interval_vars["tag_id"].set("3")
        self.tag_form.read_field("tag_id")
        self.assertTrue(self.tag_form.auto_read_active.get("tag_id"))

        # 2. Remove interval value (clear to empty or placeholder)
        self.tag_form.interval_vars["tag_id"].set("")

        # 3. Click Read button
        self.mock_reader.write_bytes.reset_mock()
        self.tag_form.read_field("tag_id")

        # 4. Verify interval is stopped and normal read command was transmitted
        self.assertFalse(self.tag_form.auto_read_active.get("tag_id"))
        self.assertIsNone(self.tag_form.auto_read_intervals.get("tag_id"))
        self.assertNotIn("tag_id", self.tag_form.auto_read_jobs)
        self.mock_reader.write_bytes.assert_called_once_with(bytes.fromhex("24110100E1F023"))

    def test_interval_stops_when_placeholder_restored_and_read_clicked(self):
        # 1. Start interval
        self.tag_form.interval_vars["tag_id"].set("5")
        self.tag_form.read_field("tag_id")
        self.assertTrue(self.tag_form.auto_read_active.get("tag_id"))

        # 2. Set back to placeholder
        self.tag_form.interval_vars["tag_id"].set(AUTO_READ_PLACEHOLDER)

        # 3. Click Read button
        self.mock_reader.write_bytes.reset_mock()
        self.tag_form.read_field("tag_id")

        # 4. Verify interval is stopped and single read transmitted
        self.assertFalse(self.tag_form.auto_read_active.get("tag_id"))
        self.assertIsNone(self.tag_form.auto_read_intervals.get("tag_id"))
        self.assertNotIn("tag_id", self.tag_form.auto_read_jobs)
        self.mock_reader.write_bytes.assert_called_once_with(bytes.fromhex("24110100E1F023"))


if __name__ == "__main__":
    unittest.main()
