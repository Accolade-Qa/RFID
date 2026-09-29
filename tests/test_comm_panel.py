"""Unit tests for CommPanelFrame component, UI control locking, and Diagnostic Result Cards."""

import pytest
import tkinter as tk
import ttkbootstrap as ttkb
from ui.components.comm_panel import CommPanelFrame


class DummyReader:
    def __init__(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def set_disconnect_callback(self, cb):
        pass

class DummyLogConsole:
    def append(self, msg):
        pass

    def append_json(self, **kwargs):
        pass


import unittest


class TestCommPanel(unittest.TestCase):
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
        self.comm_panel = CommPanelFrame(
            parent_frame=self.root,
            reader=self.reader,
            log_console_getter=lambda: DummyLogConsole(),
            on_connection_change_cb=lambda conn: None,
        )

    def test_comm_panel_initial_disconnected_state(self):
        assert self.comm_panel.title_label.cget("text") == "Disconnected"
        assert str(self.comm_panel.connect_button.cget("state")) in ("normal", "0")
        assert str(self.comm_panel.disconnect_button.cget("state")) in ("disabled", "disabled")

    def test_comm_panel_show_connected(self):
        self.comm_panel.show_connected("COM3", 115200)

        assert self.comm_panel.title_label.cget("text") == "Connected"
        assert "COM3 @ 115200" in self.comm_panel.subtext_label.cget("text")
        # Dropdowns should be locked (disabled)
        assert str(self.comm_panel.port_combobox.cget("state")) == "disabled"
        assert str(self.comm_panel.baud_combobox.cget("state")) == "disabled"

    def test_comm_panel_show_pass(self):
        self.comm_panel.show_pass("MA3EVA1234VLTD001")
        assert self.comm_panel.title_label.cget("text") == "PASS"
        assert "MA3EVA1234VLTD001" in self.comm_panel.subtext_label.cget("text")

    def test_comm_panel_show_fail_with_error_code(self):
        self.comm_panel.show_fail(error_code=0x05)  # CRC Error
        assert self.comm_panel.title_label.cget("text") == "FAIL"
        assert "0x05" in self.comm_panel.subtext_label.cget("text")
        assert "CRC" in self.comm_panel.subtext_label.cget("text")

    def test_comm_panel_show_timeout(self):
        self.comm_panel.show_timeout("Trailer VIN")
        assert self.comm_panel.title_label.cget("text") == "NO RESPONSE"
        assert "Trailer VIN" in self.comm_panel.subtext_label.cget("text")

    def test_comm_panel_show_disconnected(self):
        self.comm_panel.show_disconnected()
        assert self.comm_panel.title_label.cget("text") == "Disconnected"
        assert str(self.comm_panel.port_combobox.cget("state")) == "readonly"
        assert str(self.comm_panel.baud_combobox.cget("state")) == "readonly"
