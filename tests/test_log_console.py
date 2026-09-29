"""Unit tests for LogConsole widget, JSON audit trail recording, and auto-save log persistence."""

import os
import json
import pytest
import tkinter as tk
from logger.log_console import LogConsole, write_log


import unittest


class TestLogConsole(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.root = self.__class__.root

    def test_log_console_append_line(self):
        log_console = LogConsole(self.root)
        log_console.append("Test log entry")
        text = log_console.get("1.0", "end").strip()
        assert "Test log entry" in text
        assert log_console.line_count == 1

    def test_log_console_max_lines_capping(self):
        log_console = LogConsole(self.root, max_lines=5)
        for i in range(10):
            log_console.append(f"Line {i}")

        assert log_console.line_count <= 5
        text = log_console.get("1.0", "end").strip()
        assert "Line 0" not in text
        assert "Line 9" in text

    def test_log_console_append_json_file_persistence(self, tmp_path):
        json_path = str(tmp_path / "test_records.json")
        log_console = LogConsole(self.root)
        log_console.json_file_path = json_path

        record = log_console.append_json(
            name="VIN",
            operation="Write",
            command_sent="24 11 17 29 02 ... 23",
            response_received="24 EF 17 42 ... 23",
            conversion="alphanumeric",
            medium="CAN",
        )

        assert record["Name"] == "VIN"
        assert record["Operation"] == "Write"
        assert record["Medium of transmission"] == "CAN"
        assert "Time Stamp" in record

        # Verify saved file contents
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["Name"] == "VIN"

    def test_log_console_auto_save_text_file(self, tmp_path):
        log_path = str(tmp_path / "activity.log")
        log_console = LogConsole(self.root)
        log_console.set_file_path(log_path)
        log_console.enable_auto_save(True)

        log_console.append("Auto-saved line 1")
        log_console.append("Auto-saved line 2")

        assert os.path.exists(log_path)
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Auto-saved line 1" in content
            assert "Auto-saved line 2" in content

    def test_log_console_clear(self):
        log_console = LogConsole(self.root)
        log_console.append("Sample text")
        log_console.clear()
        text = log_console.get("1.0", "end").strip()
        assert text == ""
        assert log_console.line_count == 0

    def test_write_log_helper(self):
        log_console = LogConsole(self.root)
        write_log("Helper message", log_console)
        text = log_console.get("1.0", "end").strip()
        assert "Helper message" in text
