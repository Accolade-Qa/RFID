"""Asynchronous, non-blocking Threaded CAN Bus Reader/Writer with dynamic CAN ID mapping and Virtual Simulation Mode."""

import queue
import threading
import time
import sys
from communication.base import BaseCommunicator
from config import (
    CAN_CHANNEL,
    CAN_BUS_TYPE,
    CAN_BITRATE,
    CAN_DEFAULT_TX_ID,
    CAN_DEFAULT_RX_ID,
    CAN_IS_EXTENDED_ID,
    CAN_ID_MAP,
)

try:
    import can
    HAS_PYTHON_CAN = True
except ImportError:
    can = None
    HAS_PYTHON_CAN = False


class CANReader(BaseCommunicator):
    """
    Fully asynchronous, non-blocking Threaded CAN Bus Reader/Writer.
    Provides identical interface to SerialReader for seamless UI integration.
    Includes built-in Virtual CAN Responder for loopback simulation without hardware.
    """

    def __init__(
        self,
        channel: str = CAN_CHANNEL,
        bustype: str = CAN_BUS_TYPE,
        bitrate: int = CAN_BITRATE,
        default_tx_id: int = CAN_DEFAULT_TX_ID,
        default_rx_id: int = CAN_DEFAULT_RX_ID,
        is_extended_id: bool = CAN_IS_EXTENDED_ID,
        id_map: dict = None,
    ):
        self.channel = channel
        self.bustype = bustype
        self.bitrate = bitrate
        self.tx_id = default_tx_id
        self.rx_id = default_rx_id
        self.is_extended_id = is_extended_id
        self.id_map = id_map if id_map is not None else dict(CAN_ID_MAP)

        self.bus = None
        self.raw_queue = queue.Queue(maxsize=2000)
        self.tx_queue = queue.Queue(maxsize=1000)
        self.running = False
        self.connected = False
        self.on_disconnect_callback = None
        self.is_virtual = False

        # Reassembly buffer for multi-frame CAN transmissions
        self._rx_reassembly_buffer = bytearray()
        self._last_rx_time = 0.0

    def set_disconnect_callback(self, callback):
        """Set callback to notify UI thread when connection drops asynchronously."""
        self.on_disconnect_callback = callback

    def update_can_ids(self, tx_id: int = None, rx_id: int = None, is_extended: bool = None, id_map: dict = None):
        """
        Dynamically update transmit ID, receive ID, extended mode, or per-parameter CAN ID map.
        Automatically applied to all subsequent CAN message transmissions and filters.
        """
        if tx_id is not None:
            self.tx_id = tx_id
        if rx_id is not None:
            self.rx_id = rx_id
        if is_extended is not None:
            self.is_extended_id = is_extended
        if id_map is not None:
            self.id_map.update(id_map)

        if self.is_connected():
            self._apply_filters()

    def _apply_filters(self):
        """Apply hardware/software filters on active CAN bus based on configured RX IDs."""
        if not self.bus or not hasattr(self.bus, "set_filters"):
            return

        try:
            rx_ids = {self.rx_id}
            for param_cfg in self.id_map.values():
                if isinstance(param_cfg, dict) and "rx_id" in param_cfg:
                    rx_ids.add(param_cfg["rx_id"])

            filters = [
                {"can_id": rx_id, "can_mask": 0x1FFFFFFF if self.is_extended_id else 0x7FF, "extended": self.is_extended_id}
                for rx_id in rx_ids
            ]
            self.bus.set_filters(filters)
        except Exception:
            pass

    def connect(
        self,
        port_or_channel: str = None,
        baud_or_bitrate: int = None,
        port: str = None,
        baudrate: int = None,
    ) -> bool:
        """Connect to specified CAN interface channel and bitrate."""
        if self.connected:
            return True

        if port is not None and port_or_channel is None:
            port_or_channel = port
        if baudrate is not None and baud_or_bitrate is None:
            baud_or_bitrate = baudrate

        target_channel = str(port_or_channel if port_or_channel is not None else self.channel)
        target_bitrate = baud_or_bitrate if baud_or_bitrate is not None else self.bitrate

        ch_upper = target_channel.upper()
        b_type = self.bustype

        if "VIRTUAL" in ch_upper or b_type == "virtual" or target_channel in ("0", "1", "vcan0"):
            b_type = "virtual"
        elif "PCAN" in ch_upper:
            b_type = "pcan"
        elif "SLCAN" in ch_upper or ("COM" in ch_upper and "PCAN" not in ch_upper):
            b_type = "slcan"
        elif target_channel.startswith("can") or target_channel.startswith("vcan"):
            if sys.platform.startswith("win"):
                b_type = "virtual"
            else:
                b_type = "socketcan"

        self.is_virtual = (b_type == "virtual")

        if HAS_PYTHON_CAN:
            try:
                self.bus = can.Bus(
                    channel=target_channel if b_type != "virtual" else "0",
                    interface=b_type,
                    bitrate=int(target_bitrate),
                )
            except Exception:
                try:
                    self.bus = can.Bus(channel="0", interface="virtual", bitrate=int(target_bitrate))
                    self.is_virtual = True
                except Exception:
                    self.bus = None
        else:
            self.bus = None

        self.channel = target_channel
        self.bitrate = int(target_bitrate)
        self.bustype = b_type
        self.running = True
        self.connected = True

        if self.bus:
            self._apply_filters()

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

    def _read_loop(self):
        """Background thread receiving CAN messages and handling multi-frame payload reassembly."""
        while self.running:
            if self.bus:
                try:
                    msg = self.bus.recv(timeout=0.1)
                    if msg is None:
                        if self._rx_reassembly_buffer and (time.time() - self._last_rx_time > 0.3):
                            self._flush_reassembly_buffer()
                        continue

                    matched = (msg.arbitration_id == self.rx_id)
                    if not matched:
                        for cfg in self.id_map.values():
                            if isinstance(cfg, dict) and cfg.get("rx_id") == msg.arbitration_id:
                                matched = True
                                break

                    if matched and msg.data:
                        self._process_rx_can_message(msg.data)

                except Exception:
                    if not self.is_virtual:
                        self._handle_disconnect()
                        break
            else:
                time.sleep(0.05)

    def _process_rx_can_message(self, data: bytes):
        """Reassemble incoming CAN frames into full binary protocol frames ($...#)."""
        now = time.time()
        if self._rx_reassembly_buffer and (now - self._last_rx_time > 0.3):
            self._flush_reassembly_buffer()

        self._last_rx_time = now
        self._rx_reassembly_buffer.extend(data)
        # Check if complete frame received based on expected length and trailer byte 0x23
        if 0x24 in self._rx_reassembly_buffer:
            start_idx = self._rx_reassembly_buffer.index(0x24)
            if start_idx > 0:
                del self._rx_reassembly_buffer[:start_idx]
            if len(self._rx_reassembly_buffer) >= 3:
                expected_len = self._rx_reassembly_buffer[2] + 4
                if len(self._rx_reassembly_buffer) >= expected_len:
                    if self._rx_reassembly_buffer[expected_len - 1] == 0x23:
                        self._flush_reassembly_buffer()
        elif len(self._rx_reassembly_buffer) >= 5 and self._rx_reassembly_buffer[-1] == 0x23:
            self._flush_reassembly_buffer()

    def _flush_reassembly_buffer(self):
        if not self._rx_reassembly_buffer:
            return
        payload = bytes(self._rx_reassembly_buffer)
        self._rx_reassembly_buffer.clear()
        try:
            self.raw_queue.put_nowait(payload)
        except queue.Full:
            try:
                self.raw_queue.get_nowait()
                self.raw_queue.put_nowait(payload)
            except Exception:
                pass

    def _write_loop(self):
        """Background thread transmitting CAN frames and triggering virtual responses in virtual mode."""
        while self.running:
            try:
                item = self.tx_queue.get(timeout=0.1)
                if not item:
                    continue

                data, tx_id, is_ext = item

                # If physical CAN bus is open, transmit CAN messages
                if self.bus and not self.is_virtual:
                    try:
                        # Split data into 8-byte CAN frames
                        for i in range(0, len(data), 8):
                            chunk = data[i : i + 8]
                            msg = can.Message(
                                arbitration_id=tx_id,
                                data=chunk,
                                is_extended_id=is_ext,
                            )
                            self.bus.send(msg)
                            time.sleep(0.002)
                    except Exception:
                        pass

                # If operating in Virtual Simulation mode, generate simulated RFID tag response
                if self.is_virtual:
                    self._generate_virtual_response(data)

            except queue.Empty:
                continue
            except Exception:
                if not self.is_virtual:
                    self._handle_disconnect()
                    break

    def _generate_virtual_response(self, tx_data: bytes):
        """Simulate realistic RFID reader positive response frames in Virtual CAN mode."""
        if len(tx_data) < 5 or tx_data[0] != 0x24:
            return

        # Frame formats:
        # READ Command: 24 11 01 <PARAM_ID> <CRC_H> <CRC_L> 23 -> tx_data[3] is PARAM_ID
        # WRITE Command: 24 11 <LEN> 29 <PARAM_ID> <PAYLOAD> <CRC_H> <CRC_L> 23 -> tx_data[3] is 0x29, tx_data[4] is PARAM_ID
        if tx_data[3] == 0x29:
            cmd_type = 0x29
            param_id = tx_data[4]
        else:
            cmd_type = 0x01
            param_id = tx_data[3]

        # Simulate brief reader processing delay (20ms)
        time.sleep(0.02)

        # 1. READ Commands
        if cmd_type == 0x01:
            if param_id == 0x00:  # Tag ID
                resp = b"\x24\xEF\x12\x40\x45\x32\x38\x30\x36\x38\x32\x30\x30\x30\x30\x30\x30\x30\x30\x8E\x7F\x23"
            elif param_id == 0x01:  # Serial
                resp = b"\x24\xEF\x17\x41\x53\x45\x52\x49\x41\x4C\x31\x32\x33\x34\x56\x4C\x54\x44\x30\x31\x8E\x7F\x23"
            elif param_id == 0x02:  # VIN
                resp = b"\x24\xEF\x17\x42\x4D\x41\x33\x45\x56\x41\x31\x32\x33\x34\x56\x4C\x54\x44\x30\x31\x8E\x7F\x23"
            elif param_id == 0x03:  # Axle Count
                resp = b"\x24\xEF\x05\x43\x00\x02\xB1\x55\x23"
            elif param_id == 0x04:  # Registration
                resp = b"\x24\xEF\x12\x44\x4D\x48\x31\x32\x41\x42\x31\x32\x33\x34\x8E\x7F\x23"
            elif param_id == 0x05:  # GVW (Decimal e.g. 45000.50 -> 4500050 = 0x0044B00A)
                resp = b"\x24\xEF\x07\x45\x00\x44\xB0\x0A\xB1\x55\x23"
            elif param_id == 0x06:  # TA Cert
                resp = b"\x24\xEF\x05\x46\x12\x34\x81\x36\x23"
            else:
                return

        # 2. WRITE Commands
        elif cmd_type == 0x29:
            payload_written = tx_data[5:-3]
            resp_tag = 0x40 + param_id
            resp = bytes([0x24, 0xEF, len(payload_written) + 3, resp_tag]) + payload_written + b"\x8E\x7F\x23"

        else:
            return

        try:
            self.raw_queue.put_nowait(resp)
        except Exception:
            pass

    def _handle_disconnect(self):
        was_connected = self.connected
        self.running = False
        self.connected = False
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass
            self.bus = None

        if was_connected and callable(self.on_disconnect_callback):
            try:
                self.on_disconnect_callback()
            except Exception:
                pass

    def disconnect(self):
        self._handle_disconnect()

    def stop(self):
        self.disconnect()

    def is_connected(self) -> bool:
        return self.connected

    def get_raw_data(self) -> bytes | None:
        if not self.raw_queue.empty():
            try:
                return self.raw_queue.get_nowait()
            except queue.Empty:
                return None
        return None

    def get_raw_batch(self, max_items: int = 50) -> list[bytes]:
        batch = []
        for _ in range(max_items):
            if self.raw_queue.empty():
                break
            try:
                batch.append(self.raw_queue.get_nowait())
            except queue.Empty:
                break
        return batch

    def write_bytes(self, data: bytes, param_id: int = None) -> bool:
        """
        Queue raw binary frame bytes for transmission over CAN bus.
        Automatically checks dynamic CAN ID map for param_id specific Tx ID if provided.
        """
        if not self.is_connected():
            return False

        tx_id = self.tx_id
        is_ext = self.is_extended_id

        if param_id is None and len(data) >= 5 and data[0] == 0x24:
            if data[3] == 0x29:
                param_id = data[4]
            else:
                param_id = data[3]

        if param_id is not None and param_id in self.id_map:
            cfg = self.id_map[param_id]
            if isinstance(cfg, dict):
                tx_id = cfg.get("tx_id", tx_id)
                is_ext = cfg.get("is_extended", is_ext)

        try:
            self.tx_queue.put_nowait((data, tx_id, is_ext))
            return True
        except queue.Full:
            return False
