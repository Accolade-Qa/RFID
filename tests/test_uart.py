"""Unit tests for Threaded UART SerialReader communicator."""

import pytest
import queue
from communication.uart import SerialReader


class TestSerialReader:
    def test_uart_init_defaults(self):
        reader = SerialReader(port="COM99", baudrate=115200)
        assert reader.port == "COM99"
        assert reader.baudrate == 115200
        assert reader.is_connected() is False
        assert reader.ser is None

    def test_uart_connect_non_existent_port_returns_false(self):
        reader = SerialReader(port="COM999", baudrate=115200)
        success = reader.connect()
        assert success is False
        assert reader.is_connected() is False

    def test_uart_write_bytes_when_disconnected_returns_false(self):
        reader = SerialReader(port="COM99")
        result = reader.write_bytes(b"\x24\x11\x01\x00\x23")
        assert result is False

    def test_uart_write_line_when_disconnected_returns_false(self):
        reader = SerialReader(port="COM99")
        result = reader.write_line("TEST_COMMAND")
        assert result is False

    def test_uart_get_raw_batch_when_empty(self):
        reader = SerialReader()
        batch = reader.get_raw_batch()
        assert isinstance(batch, list)
        assert len(batch) == 0

    def test_uart_get_raw_batch_when_populated(self):
        reader = SerialReader()
        reader.raw_queue.put(b"\x24\xEF\x05\x43\x00\x02\x23")
        batch = reader.get_raw_batch()
        assert len(batch) == 1
        assert batch[0] == b"\x24\xEF\x05\x43\x00\x02\x23"

    def test_uart_disconnect_callback_trigger(self):
        callback_called = False

        def on_disconnect():
            nonlocal callback_called
            callback_called = True

        reader = SerialReader()
        reader.set_disconnect_callback(on_disconnect)
        reader.connected = True  # Simulate established state
        reader.disconnect()

        assert reader.is_connected() is False
        assert callback_called is True

    def test_uart_probe_port_non_existent_returns_false(self):
        reader = SerialReader()
        assert reader.probe_port("COM999", probe_time=0.1) is False
