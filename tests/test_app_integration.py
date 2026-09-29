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

class TestNoDataResponses:
    def setup_method(self):
        self.app = RFIDApp.__new__(RFIDApp)
        self.log_mock = DummyLogConsole()
        self.app.log_panel_comp = type("LogPanel", (), {"log_console": self.log_mock})()
        self.app.tag_form_comp = DummyTagForm()
        self.app.comm_panel_comp = DummyCommPanel()

    def test_zero_tag_id_fails_without_populating_field(self):
        failures = []
        self.app.tag_form_comp.pending_requests[0x00] = {
            "req_id": 1,
            "Name": "Tag ID",
            "Operation": "Read",
            "Command Sent": "24 11 01 00 23",
            "Conversion": "hex as it is",
            "var_name": "tag_id",
            "on_failure": failures.append,
        }

        frame = b"\x24\xEF\x12\x40" + (b"\x00" * 12) + b"\x00\x00\x23"
        self.app._parse_uart_response(frame)

        assert self.app.tag_form_comp.get_field_value("tag_id") == ""
        assert self.app.comm_panel_comp.title_label.cget("text") == "FAIL"
        assert "No ID/data found" in self.app.comm_panel_comp.subtext_label.cget("text")
        assert failures == ["NO_DATA"]

    def test_tag_id_error_07_clears_value_and_keeps_failure_message(self):
        failures = []
        self.app.tag_form_comp.set_field_value("tag_id", "E28068900000000000000001")
        self.app.tag_form_comp.pending_requests[0x00] = {
            "req_id": 3,
            "Name": "Tag ID",
            "Operation": "Read",
            "Command Sent": "24 11 01 00 23",
            "Conversion": "hex as it is",
            "var_name": "tag_id",
            "on_failure": failures.append,
        }

        self.app._parse_uart_response(b"\x24\xEF\x05\x7F\x00\x07\x00\x00\x23")

        assert self.app.tag_form_comp.get_field_value("tag_id") == ""
        assert self.app.comm_panel_comp.title_label.cget("text") == "FAIL"
        assert "0x07" in self.app.comm_panel_comp.subtext_label.cget("text")
        assert "No Tag / Data Unavailable" in self.app.comm_panel_comp.subtext_label.cget("text")
        assert failures == [7]
        assert 0x00 not in self.app.tag_form_comp.pending_requests
        assert len(self.log_mock.json_records) == 1

    def test_zero_numeric_data_fails_without_populating_field(self):
        failures = []
        self.app.tag_form_comp.pending_requests[0x03] = {
            "req_id": 2,
            "Name": "Axle Count",
            "Operation": "Read",
            "Command Sent": "24 11 01 03 23",
            "Conversion": "numerical",
            "var_name": "axle",
            "on_failure": failures.append,
        }

        frame = b"\x24\xEF\x06\x43\x00\x00\x00\x00\x23"
        self.app._parse_uart_response(frame)

        assert self.app.tag_form_comp.get_field_value("axle") == ""
        assert self.app.comm_panel_comp.title_label.cget("text") == "FAIL"
        assert "No ID/data found" in self.app.comm_panel_comp.subtext_label.cget("text")
        assert failures == ["NO_DATA"]


class DummyTagForm:
    def __init__(self):
        self.pending_requests = {}
        self.field_values = {"tag_id": "", "axle": ""}

    def set_field_value(self, field_name, value):
        self.field_values[field_name] = value

    def get_field_value(self, field_name):
        return self.field_values[field_name]


class DummyLabel:
    def __init__(self):
        self.text = ""

    def cget(self, option):
        return self.text

    def configure(self, **kwargs):
        self.text = kwargs.get("text", self.text)


class DummyCommPanel:
    def __init__(self):
        self.title_label = DummyLabel()
        self.subtext_label = DummyLabel()

    def show_fail(self, error_code=None, description=""):
        self.title_label.configure(text="FAIL")
        if error_code is not None:
            detail = ERROR_CODES.get(error_code, "Unknown error")
            self.subtext_label.configure(text=f"Error 0x{error_code:02X}: {detail}")
        else:
            self.subtext_label.configure(text=f"Failure: {description}")

    def show_pass(self, value):
        self.title_label.configure(text="PASS")
        self.subtext_label.configure(text=f"Positive response: {value}")
