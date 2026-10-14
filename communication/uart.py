import queue
import threading
import time
import serial
from serial.tools import list_ports
from typing import List, Optional
from communication.base import BaseCommunicator


class SerialReader(BaseCommunicator):
    """Fully asynchronous, non-blocking Threaded UART Serial Port Reader/Writer."""

    def __init__(
        self,
        port: str = "COM3",
        baudrate: int = 115200,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        timeout: float = 0.1,
    ):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.ser = None
        self.raw_queue = queue.Queue(maxsize=2000)
        self.tx_queue = queue.Queue(maxsize=1000)
        self.running = False
        self.connected = False
        self.on_disconnect_callbacks = []

    def set_disconnect_callback(self, callback):
        """Register a callback to notify UI when the connection is broken asynchronously."""
        if callback is None:
            return
        if callback not in self.on_disconnect_callbacks:
            self.on_disconnect_callbacks.append(callback)

    def connect(
        self,
        port: str = None,
        baudrate: int = None,
        bytesize: int = None,
        parity: str = None,
        stopbits: int = None,
        timeout: float = None,
        port_or_channel: str = None,
        baud_or_bitrate: int = None,
    ) -> bool:
        if self.connected:
            return True

        if port_or_channel is not None:
            port = port_or_channel
        if baud_or_bitrate is not None:
            baudrate = baud_or_bitrate

        target_port = port if port is not None else self.port
        target_baud = baudrate if baudrate is not None else self.baudrate
        target_bytesize = bytesize if bytesize is not None else self.bytesize
        target_parity = parity if parity is not None else self.parity
        target_stopbits = stopbits if stopbits is not None else self.stopbits
        target_timeout = timeout if timeout is not None else self.timeout

        # Check port existence before attempting blocking open
        try:
            available_ports = [p.device for p in list_ports.comports()]
            if available_ports and target_port not in available_ports:
                return False
        except Exception:
            pass

        try:
            self.ser = serial.Serial(
                port=target_port,
                baudrate=target_baud,
                bytesize=target_bytesize,
                parity=target_parity,
                stopbits=target_stopbits,
                timeout=target_timeout,
                write_timeout=0.2,  # Prevent blocking on write
            )
            self.port = target_port
            self.baudrate = target_baud
            self.running = True
            self.connected = True

            # Clear queues on new connection
            while not self.raw_queue.empty():
                try:
                    self.raw_queue.get_nowait()
                except Exception:
                    break
            while not self.tx_queue.empty():
                try:
                    self.tx_queue.get_nowait()
                except Exception:
                    break

            threading.Thread(target=self._read_loop, daemon=True).start()
            threading.Thread(target=self._write_loop, daemon=True).start()
            return True
        except Exception:
            self._handle_disconnect()
            return False

    def _read_loop(self):
        while self.running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting:
                    raw = self.ser.read(self.ser.in_waiting)
                    if raw:
                        try:
                            self.raw_queue.put_nowait(raw)
                        except queue.Full:
                            try:
                                self.raw_queue.get_nowait()
                                self.raw_queue.put_nowait(raw)
                            except Exception:
                                pass
                else:
                    time.sleep(0.01)
            except Exception:
                self._handle_disconnect()
                break

    def _write_loop(self):
        """Background thread handling non-blocking serial transmissions."""
        while self.running and self.ser and self.ser.is_open:
            try:
                data = self.tx_queue.get(timeout=0.1)
                if data and self.ser and self.ser.is_open:
                    self.ser.write(data)
            except queue.Empty:
                continue
            except Exception:
                self._handle_disconnect()
                break

    def _handle_disconnect(self):
        was_connected = self.connected
        self.running = False
        self.connected = False
        if self.ser:
            try:
                if hasattr(self.ser, "cancel_read"):
                    self.ser.cancel_read()
                if hasattr(self.ser, "cancel_write"):
                    self.ser.cancel_write()
                self.ser.close()
            except Exception:
                pass
            self.ser = None

        if was_connected:
            for callback in list(self.on_disconnect_callbacks):
                try:
                    callback()
                except Exception:
                    pass

    def disconnect(self):
        self._handle_disconnect()

    def stop(self):
        """Alias for disconnect."""
        self.disconnect()

    def is_connected(self) -> bool:
        return self.connected and self.ser is not None and self.ser.is_open

    def get_raw_data(self) -> Optional[bytes]:
        if not self.raw_queue.empty():
            try:
                return self.raw_queue.get_nowait()
            except queue.Empty:
                return None
        return None

    def get_raw_batch(self, max_items: int = 50) -> List[bytes]:
        batch = []
        for _ in range(max_items):
            if self.raw_queue.empty():
                break
            try:
                batch.append(self.raw_queue.get_nowait())
            except queue.Empty:
                break
        return batch

    def write_line(self, data: str) -> bool:
        """Non-blocking queue write. Returns True if queued successfully."""
        if not self.is_connected():
            return False
        try:
            self.tx_queue.put_nowait(data.encode("utf-8"))
            return True
        except queue.Full:
            return False

    def write_bytes(self, data: bytes) -> bool:
        """Non-blocking queue byte write. Returns True if queued successfully."""
        if not self.is_connected():
            return False
        try:
            self.tx_queue.put_nowait(data)
            return True
        except queue.Full:
            return False

    def probe_port(self, port: str = None, baudrate: int = None, probe_time: float = 0.5) -> bool:
        target_port = port or self.port
        target_baud = baudrate or self.baudrate
        try:
            with serial.Serial(
                port=target_port,
                baudrate=target_baud,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=0.1,
                write_timeout=0.1,
            ) as ser:
                start = time.time()
                while time.time() - start < probe_time:
                    if ser.in_waiting:
                        ser.readline()
                        return True
                    time.sleep(0.05)
                return False
        except Exception:
            return False
