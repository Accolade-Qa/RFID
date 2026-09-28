"""Unit tests for TagFormFrame component, placeholders, field actions, and timeout manager."""

import pytest
import time
import tkinter as tk
import ttkbootstrap as ttkb
from ui.components.tag_form import TagFormFrame, READ_COMMANDS, PLACEHOLDERS


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

    def append_json(self, **kwargs):
        pass


import unittest


class TestTagForm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ttkb.Window(themename="darkly")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.root = self.__class__.root
        self.reader = DummyReader()
        self.timeout_called_with = None

        def on_timeout(cmd_name):
            self.timeout_called_with = cmd_name

        self.tag_form = TagFormFrame(
            parent_frame=self.root,
            root=self.root,
            reader=self.reader,
            log_console_getter=lambda: DummyLogConsole(),
            timeout_cb=on_timeout,
        )

    def tearDown(self):
        self.tag_form.clear_pending_requests()

    def test_tag_form_initialization(self):
        assert "vin" in self.tag_form.field_vars
        assert "serial" in self.tag_form.field_vars
        assert "gvw" in self.tag_form.field_vars
        assert self.tag_form.field_vars["vin"].get() == PLACEHOLDERS["vin"]

    def test_tag_form_get_and_set_field_value(self):
        # Setting value clears placeholder
        self.tag_form.set_field_value("vin", "MA3EVA1234VLTD001")
        assert self.tag_form.get_field_value("vin") == "MA3EVA1234VLTD001"

        # Placeholder returns empty string when retrieved
        self.tag_form.set_field_value("serial", PLACEHOLDERS["serial"])
        assert self.tag_form.get_field_value("serial") == ""

    def test_tag_form_read_field_connected(self):
        self.tag_form.read_field("vin")
        assert len(self.reader.written_bytes) == 1
        expected_cmd = bytes.fromhex(READ_COMMANDS["vin"][0])
        assert self.reader.written_bytes[0] == expected_cmd
        assert 0x02 in self.tag_form.pending_requests

    def test_tag_form_read_field_disconnected(self):
        self.reader._connected = False
        self.tag_form.read_field("vin")
        # Should not write bytes when disconnected
        assert len(self.reader.written_bytes) == 0

    def test_tag_form_write_field_empty_value(self):
        self.tag_form.set_field_value("vin", "")
        self.tag_form.write_field("vin")
        # Should not write bytes if field is empty
        assert len(self.reader.written_bytes) == 0

    def test_tag_form_write_field_valid_value(self):
        self.tag_form.set_field_value("vin", "MA3EVA1234VLTD001")
        self.tag_form.write_field("vin")
        assert len(self.reader.written_bytes) == 1
        assert 0x02 in self.tag_form.pending_requests
        req_info = self.tag_form.pending_requests[0x02]
        assert req_info["Name"] == "Trailer VIN"
        assert req_info["Operation"] == "Write"

    def test_tag_form_request_timeout_handler(self):
        self.tag_form.set_field_value("vin", "MA3EVA1234VLTD001")
        self.tag_form.write_field("vin")

        param_id = 0x02
        assert param_id in self.tag_form.pending_requests
        req_id = self.tag_form.pending_requests[param_id]["req_id"]

        # Manually trigger timeout handler
        self.tag_form._handle_request_timeout(param_id, req_id, "Trailer VIN", "Write")

        assert param_id not in self.tag_form.pending_requests
        assert self.timeout_called_with == "Trailer VIN"

    def test_tag_form_clear_fields_resets_form(self):
        self.tag_form.set_field_value("vin", "MA3EVA1234VLTD001")
        self.tag_form.set_field_value("axle", "3")
        self.tag_form.clear_fields()

        assert self.tag_form.get_field_value("vin") == ""
        assert self.tag_form.field_vars["vin"].get() == PLACEHOLDERS["vin"]
        assert len(self.tag_form.pending_requests) == 0
