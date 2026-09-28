"""Unit tests for CommPanelFrame component, UI control locking, and Diagnostic Result Cards."""

import pytest
import tkinter as tk
import ttkbootstrap as ttkb
from ui.components.comm_panel import CommPanelFrame


class DummyReader:
    def __init__(self):
        self.connected = False
        self.tx_id = 0x7E0
        self.rx_id = 0x7E8
        self.is_extended_id = False
        self.id_map = {}

    def is_connected(self):
        return self.connected

    def set_disconnect_callback(self, cb):
        pass

    def update_can_ids(self, tx_id=None, rx_id=None, is_extended=None, id_map=None):
        if tx_id is not None:
            self.tx_id = tx_id
        if rx_id is not None:
            self.rx_id = rx_id
        if is_extended is not None:
            self.is_extended_id = is_extended
        if id_map is not None:
            self.id_map.update(id_map)


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
            on_medium_change_cb=lambda med: None,
        )

    def test_comm_panel_initial_disconnected_state(self):
        assert self.comm_panel.title_label.cget("text") == "Disconnected"
        assert self.comm_panel.medium_var.get() == "UART"
        assert str(self.comm_panel.connect_button.cget("state")) in ("normal", "0")
        assert str(self.comm_panel.disconnect_button.cget("state")) in ("disabled", "disabled")

    def test_comm_panel_medium_switch_to_can(self):
        self.comm_panel.medium_var.set("CAN")
        self.comm_panel._on_medium_selected()

        assert self.comm_panel.port_var.get() in ["PCAN_USBBUS1", "PCAN_USBBUS2", "can0", "vcan0", "SLCAN", "COM3"]
        assert self.comm_panel.baud_var.get() in ["125000", "250000", "500000", "1000000"]
        # CAN IDs button should be managed
        assert self.comm_panel.can_id_button.winfo_manager() != ""

    def test_comm_panel_show_connected(self):
        self.comm_panel.show_connected("COM3", 115200)

        assert self.comm_panel.title_label.cget("text") == "Connected"
        assert "COM3 @ 115200" in self.comm_panel.subtext_label.cget("text")
        # Dropdowns should be locked (disabled)
        assert str(self.comm_panel.medium_combobox.cget("state")) == "disabled"
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
        assert str(self.comm_panel.medium_combobox.cget("state")) == "readonly"
