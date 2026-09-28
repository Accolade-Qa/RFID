"""Integration tests for RFIDApp frame parsing, buffer management, negative responses, and medium swapping."""

import pytest
import tkinter as tk
import ttkbootstrap as ttkb
from ui.app import RFIDApp
from config import ERROR_CODES


class DummyLogConsole:
    def __init__(self):
        self.logs = []
        self.json_records = []

    def append(self, message):
        self.logs.append(message)

    def append_json(self, **kwargs):
        self.json_records.append(kwargs)
        return kwargs


    def setUp(self):
        self.app = RFIDApp()
        self.app.root.withdraw()

    def tearDown(self):
        try:
            self.app.on_close()
        except Exception:
            pass

    def test_hex_bytes_from_text_helper(self):
        assert RFIDApp._hex_bytes_from_text("24 11 01 02 23") == b"\x24\x11\x01\x02\x23"
        assert RFIDApp._hex_bytes_from_text("0x240x11") == b"\x24\x11"
        assert RFIDApp._hex_bytes_from_text("INVALID") is None
        assert RFIDApp._hex_bytes_from_text("123") is None  # Odd length

    def test_parse_uart_response_tag_id_positive(self):
        app = self.app
        log_mock = DummyLogConsole()
        app.log_panel_comp.log_console = log_mock

        # Register pending request for Tag ID (param_id 0x00)
        app.tag_form_comp.pending_requests[0x00] = {
            "req_id": 1,
            "Name": "Tag ID",
            "Operation": "Read",
            "Command Sent": "24 11 01 00 23",
            "Conversion": "hex as it is",
            "var_name": "tag_id",
        }

        # 24 EF 12 40 45323830363832303030303030303023
        frame = b"\x24\xEF\x12\x40\x45\x32\x38\x30\x36\x38\x32\x30\x30\x30\x30\x30\x30\x30\x30\x23"
        app._parse_uart_response(frame)

        assert app.tag_form_comp.get_field_value("tag_id") != ""
        assert app.comm_panel_comp.title_label.cget("text") == "PASS"
        assert len(log_mock.json_records) == 1
        assert log_mock.json_records[0]["Operation"] == "Read"

    def test_parse_uart_response_vin_positive(self):
        app = self.app
        log_mock = DummyLogConsole()
        app.log_panel_comp.log_console = log_mock

        app.tag_form_comp.pending_requests[0x02] = {
            "req_id": 2,
            "Name": "VIN",
            "Operation": "Read",
            "Command Sent": "24 11 01 02 23",
            "Conversion": "alphanumeric",
            "var_name": "vin",
        }

        # Positive VIN frame
        frame = b"\x24\xEF\x17\x42\x4D\x41\x33\x45\x56\x41\x31\x32\x33\x34\x56\x4C\x54\x44\x30\x31\x8E\x7F\x23"
        app._parse_uart_response(frame)

        assert app.tag_form_comp.get_field_value("vin") == "MA3EVA1234VLTD01"
        assert app.comm_panel_comp.title_label.cget("text") == "PASS"

    def test_parse_uart_response_negative_response_frame(self):
        app = self.app
        log_mock = DummyLogConsole()
        app.log_panel_comp.log_console = log_mock

        app.tag_form_comp.pending_requests[0x03] = {
            "req_id": 3,
            "Name": "Axle Count",
            "Operation": "Write",
            "Command Sent": "24 11 04 29 03 00 05 ... 23",
            "Conversion": "numerical",
            "var_name": "axle",
        }

        # Negative Response Frame (Tag byte 0x7F, error code 0x05 CRC Error)
        frame = b"\x24\xEF\x05\x7F\x03\x05\x8E\x7F\x23"
        app._parse_uart_response(frame)

        assert app.comm_panel_comp.title_label.cget("text") == "FAIL"
        assert "0x05" in app.comm_panel_comp.subtext_label.cget("text")
        assert 0x03 not in app.tag_form_comp.pending_requests

    def test_parse_uart_response_late_response_ignored(self):
        app = self.app
        log_mock = DummyLogConsole()
        app.log_panel_comp.log_console = log_mock

        # No pending request in memory (simulating already timed out)
        app.tag_form_comp.pending_requests.clear()

        frame = b"\x24\xEF\x17\x42\x4D\x41\x33\x45\x56\x41\x31\x32\x33\x34\x56\x4C\x54\x44\x30\x31\x8E\x7F\x23"
        app._parse_uart_response(frame)

        # Logged late response ignored
        assert any("Ignored" in log for log in log_mock.logs)

    def test_medium_swap_uart_and_can(self):
        app = self.app
        app._on_medium_change("CAN")

        assert app.reader == app.can_reader
        assert app.comm_panel_comp.reader == app.can_reader
        assert app.tag_form_comp.reader == app.can_reader

        app._on_medium_change("UART")
        assert app.reader == app.serial_reader
