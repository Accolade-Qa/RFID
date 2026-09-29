from pathlib import Path
import ttkbootstrap as ttkb

from config import (
    PORT,
    BAUDRATE,
    CAN_CHANNEL,
    CAN_BUS_TYPE,
    CAN_BITRATE,
    CAN_DEFAULT_TX_ID,
    CAN_DEFAULT_RX_ID,
    CAN_IS_EXTENDED_ID,
    CAN_ID_MAP,
    ERROR_CODES,
)
from communication import SerialReader, CANReader
from logger import write_log
from validation.validators import normalize_rel_version_value
from ui.components.header import build_header_frame
from ui.components.tag_form import TagFormFrame
from ui.components.comm_panel import CommPanelFrame
from ui.components.log_panel import LogPanelFrame


class RFIDApp:
    """Main Application orchestrator for RFID Communicator UI."""

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent

        self.root = ttkb.Window(themename="darkly")
        self.root.geometry("1450x880")
        self.root.minsize(1200, 750)
        self.root.title("RFID Tag Reader & Writer")

        self._configure_styles()
        self._set_app_icon()

        self.serial_reader = SerialReader(PORT, BAUDRATE)
        self.can_reader = CANReader(
            channel=CAN_CHANNEL,
            bustype=CAN_BUS_TYPE,
            bitrate=CAN_BITRATE,
            default_tx_id=CAN_DEFAULT_TX_ID,
            default_rx_id=CAN_DEFAULT_RX_ID,
            is_extended_id=CAN_IS_EXTENDED_ID,
            id_map=CAN_ID_MAP,
        )
        self.reader = self.serial_reader
        self.logging_enabled = False
        self.rx_buffer = bytearray()

        self.main_frame = ttkb.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.header_frame = build_header_frame(self.main_frame, self.base_dir)

        self.content_frame = ttkb.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.right_panel = ttkb.Frame(self.content_frame)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.top_row = ttkb.Frame(self.right_panel)
        self.top_row.pack(fill="x", pady=(0, 12))

        # Log panel component
        self.log_panel_comp = LogPanelFrame(self.right_panel, self.root)

        # Comm panel component
        self.comm_panel_comp = CommPanelFrame(
            self.top_row,
            self.reader,
            lambda: self.log_panel_comp.log_console,
            self._on_connection_change,
            on_medium_change_cb=self._on_medium_change,
        )

        # Tag form component
        self.tag_form_comp = TagFormFrame(
            self.content_frame,
            self.root,
            self.reader,
            lambda: self.log_panel_comp.log_console,
            reset_reader_status_cb=None,
            timeout_cb=self._on_command_timeout,
        )

        self._bind_events()
        self.root.after(50, self.update_gui)

    def _configure_styles(self):
        style = ttkb.Style(theme="darkly")

        # Uniform dark utility palette across the whole app
        dark_bg = "#111827"
        panel_bg = "#1F2937"
        panel_alt = "#0F172A"
        text_fg = "#F8FAFC"
        soft_fg = "#E2E8F0"

        style.configure("TFrame", background=panel_bg)
        style.configure("TLabel", background=panel_bg, foreground=text_fg)
        style.configure("TEntry", background=panel_alt, foreground=text_fg, fieldbackground=panel_alt, padding=(8, 6), borderwidth=1, relief="flat")
        style.configure("TCombobox", fieldbackground=panel_alt, background=panel_alt, foreground=text_fg, padding=(6, 5))
        style.configure("TButton", padding=(10, 6), borderwidth=1, relief="flat")
        style.configure("TCheckbutton", background=panel_bg, foreground=text_fg)
        style.configure("TLabelframe", background=panel_bg)
        style.configure("TLabelframe.Label", background=panel_bg, foreground=text_fg)

        style.configure("Card.TFrame", background=panel_bg)
        style.configure("Header.TFrame", background=dark_bg)
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground=text_fg, background=dark_bg)
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground=soft_fg, background=panel_bg)
        style.configure("Field.TLabel", font=("Segoe UI", 10), foreground=soft_fg, background=panel_bg)
        style.configure("Caption.TLabel", font=("Segoe UI", 9), foreground="#94a3b8", background=panel_bg)

        style.map(
            "TEntry",
            fieldbackground=[("readonly", panel_alt), ("!readonly", panel_alt)],
            foreground=[("disabled", "#94a3b8"), ("!disabled", text_fg)],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", panel_alt), ("!readonly", panel_alt)],
            foreground=[("disabled", "#94a3b8"), ("!disabled", text_fg)],
        )

    def _on_command_timeout(self, field_label: str):
        self.comm_panel_comp.show_timeout(field_label)

    def _set_app_icon(self):
        icon_path = self.base_dir / "assets" / "Acc_logo.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

    def _on_connection_change(self, connected: bool):
        if not connected:
            self.tag_form_comp.clear_pending_requests()
            self.comm_panel_comp.show_disconnected()

    def _on_medium_change(self, medium: str):
        if self.reader and self.reader.is_connected():
            self.reader.disconnect()

        self.tag_form_comp.clear_pending_requests()
        if medium == "CAN":
            self.reader = self.can_reader
        else:
            self.reader = self.serial_reader

        self.comm_panel_comp.reader = self.reader
        self.tag_form_comp.reader = self.reader
        self.reader.set_disconnect_callback(self.comm_panel_comp._on_async_disconnect)
        self.comm_panel_comp.show_disconnected()
        write_log(f"Switched communication medium to {medium}", self.log_panel_comp.log_console)

    def _bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        try:
            log_c = self.log_panel_comp.log_console
            log_c.bind("<Control-v>", self._handle_paste_to_log)
            log_c.bind("<Control-V>", self._handle_paste_to_log)
        except Exception:
            pass

    def _handle_paste_to_log(self, event=None):
        try:
            txt = self.root.clipboard_get()
        except Exception:
            return "break"

        hb = self._hex_bytes_from_text(txt.strip())
        if hb is None:
            return "break"

        log_c = self.log_panel_comp.log_console
        if self.reader.is_connected():
            self.reader.write_bytes(hb)
            write_log(f"UART TX (hex): {hb.hex(' ').upper()}", log_c)
        else:
            write_log("UART TX ignored: reader not connected", log_c)

        return "break"

    @staticmethod
    def _hex_bytes_from_text(s: str) -> bytes | None:
        filtered = s.replace("0x", "").replace("0X", "").replace(" ", "")
        if len(filtered) % 2 != 0:
            return None
        try:
            return bytes.fromhex(filtered)
        except Exception:
            return None

    def _parse_uart_response(self, frame: bytes):
        """Universal parser for UART response frames (both 24EF...23 and direct <LEN><TAG><FIELD_ID>...23)."""
        log_console = self.log_panel_comp.log_console
        medium = self.comm_panel_comp.medium_var.get()
        frame_hex = frame.hex().upper()

        try:
            if len(frame) < 5:
                self.comm_panel_comp.show_fail(description="Frame too short")
                return

            # Determine frame structure:
            # Full Frame: 24 EF <LEN> <TAG> <FIELD_ID/PAYLOAD> ... <CRC> 23 (tag_byte at frame[3])
            # Direct Frame: <LEN> <TAG> <FIELD_ID> <PAYLOAD> ... <CRC> 23 (tag_byte at frame[1])
            is_full_frame = frame.startswith(b"\x24") or (len(frame) >= 6 and frame[0] == 0x24)

            if is_full_frame:
                tag_byte = frame[3]
                header_offset = 4
            else:
                tag_byte = frame[1]
                header_offset = 2

            # Negative response check (0x7F tag byte ONLY per VLTD spec)
            if tag_byte == 0x7F:
                failed_cmd = frame[header_offset] if len(frame) > header_offset else 0
                error_code = frame[header_offset + 1] if len(frame) > (header_offset + 1) else 0x01
                if failed_cmd not in self.tag_form_comp.pending_requests and len(self.tag_form_comp.pending_requests) == 1:
                    failed_cmd = next(iter(self.tag_form_comp.pending_requests.keys()))

                if failed_cmd in self.tag_form_comp.pending_requests:
                    pending_info = self.tag_form_comp.pending_requests.pop(failed_cmd)
                    on_failure_cb = pending_info.get("on_failure")

                    self.comm_panel_comp.show_fail(error_code=error_code)
                    write_log(f"{medium} RX Negative Response for Cmd 0x{failed_cmd:02X} (Error 0x{error_code:02X}: {ERROR_CODES.get(error_code, 'Error')})", log_console)
                    log_console.append_json(
                        name=f"Cmd 0x{failed_cmd:02X}",
                        operation="Negative Response",
                        command_sent="",
                        response_received=frame_hex,
                        conversion="error",
                        medium=medium,
                    )
                    if callable(on_failure_cb):
                        try:
                            on_failure_cb(error_code)
                        except Exception:
                            pass
                else:
                    write_log(f"{medium} RX Negative Response (Error 0x{error_code:02X}: {ERROR_CODES.get(error_code, 'Error')})", log_console)
                    self.comm_panel_comp.show_fail(error_code=error_code)
                return

            # Positive Response Payload extraction using Frame's Length Byte
            length_byte = frame[2] if is_full_frame and len(frame) > 2 else (frame[0] if len(frame) > 0 else 0)

            # Check if tag_byte is 0x69 or 0x29 (SET Transmission Command ID response)
            if tag_byte in (0x69, 0x29):
                field_id = frame[header_offset] if len(frame) > header_offset else 0  # e.g. 0x03 for Axle Count
                tag_byte = 0x40 + field_id  # Normalize to 0x40+field_id tag byte (e.g. 0x43 for Axle)
                payload_start = header_offset + 1

                # Exact extraction using length byte:
                if length_byte > 0:
                    if length_byte == len(frame) - 4:  # LEN includes TAG + FIELD_ID + PAYLOAD + CRC
                        payload_len = max(0, length_byte - 4)
                    elif length_byte == len(frame) - 6:  # LEN includes CMD + FIELD_ID + PAYLOAD
                        payload_len = max(0, length_byte - 2)
                    elif length_byte <= (len(frame) - 1 - payload_start):
                        payload_len = length_byte
                    else:
                        payload_len = max(0, len(frame) - 3 - payload_start) if len(frame) >= (payload_start + 3) else max(0, len(frame) - 1 - payload_start)
                    data_bytes = frame[payload_start : payload_start + payload_len]
                else:
                    data_bytes = frame[payload_start : -3] if len(frame) >= (payload_start + 3) else frame[payload_start : -1]

            else:
                payload_start = header_offset
                if length_byte > 0:
                    if length_byte == len(frame) - 4:  # LEN includes TAG + PAYLOAD + CRC (e.g. 24 EF <LEN> 40 <DATA> <CRC> 23)
                        payload_len = max(0, length_byte - 3)
                    elif length_byte == len(frame) - 6:  # LEN includes TAG + PAYLOAD (followed by 2 CRC bytes before 23)
                        payload_len = max(0, length_byte - 1)
                    elif length_byte <= (len(frame) - 1 - payload_start):
                        # LEN specifies exact payload byte length
                        payload_len = length_byte
                    else:
                        payload_len = max(0, len(frame) - 3 - payload_start) if len(frame) >= (payload_start + 3) else max(0, len(frame) - 1 - payload_start)
                    data_bytes = frame[payload_start : payload_start + payload_len]
                else:
                    data_bytes = frame[payload_start : -3] if len(frame) >= (payload_start + 3) else frame[payload_start : -1]

            if tag_byte in (0x41, 0x42, 0x44, 0x01, 0x02, 0x04):
                clean_payload_bytes = data_bytes.rstrip(b"\x00\x20\r\n ")
                max_len = 17 if tag_byte in (0x42, 0x02) else (16 if tag_byte in (0x41, 0x01) else 12)
                if len(clean_payload_bytes) > max_len:
                    clean_payload_bytes = clean_payload_bytes[:max_len]
                payload_hex_spaced = clean_payload_bytes.hex(" ").upper().strip()
            else:
                payload_hex_spaced = data_bytes.hex(" ").upper().strip()

            var_name = ""
            field_label = ""
            conv_type = ""
            decoded_val = ""
            param_id = None

            if tag_byte in (0x40, 0x00):  # Tag EPC (0x00) -> Hex As-Is
                param_id = 0x00
                var_name = "tag_id"
                field_label = "Tag ID"
                conv_type = "hex as it is"

                # Check if data_bytes is ASCII hex representation or raw binary bytes
                is_ascii_hex = False
                try:
                    ascii_str = data_bytes.decode("ascii").strip()
                    if ascii_str and all(c in "0123456789ABCDEFabcdef" for c in ascii_str):
                        decoded_val = ascii_str.upper()
                        is_ascii_hex = True
                except Exception:
                    pass

                if not is_ascii_hex:
                    decoded_val = data_bytes.hex().upper()

                # Remove last 2 characters from response and keep exact 24 characters
                if len(decoded_val) > 24:
                    decoded_val = decoded_val[:-2]
                if len(decoded_val) > 24:
                    decoded_val = decoded_val[:24]

                payload_hex_spaced = " ".join([decoded_val[i : i + 2] for i in range(0, len(decoded_val), 2)])

            elif tag_byte in (0x41, 0x01):  # Serial Reader Number (0x01) -> Alphanumeric
                param_id = 0x01
                var_name = "serial"
                field_label = "Serial Number"
                conv_type = "alphanumeric"
                decoded_val = data_bytes.rstrip(b"\x00\x20\r\n ").decode("ascii", errors="ignore")
                if len(decoded_val) > 16:
                    decoded_val = decoded_val[:16]

            elif tag_byte in (0x42, 0x02):  # Trailer VIN (0x02) -> Alphanumeric
                param_id = 0x02
                var_name = "vin"
                field_label = "VIN"
                conv_type = "alphanumeric"
                decoded_val = data_bytes.rstrip(b"\x00\x20\r\n ").decode("ascii", errors="ignore")
                if len(decoded_val) > 17:
                    decoded_val = decoded_val[:17]

            elif tag_byte in (0x43, 0x03):  # Axle Count (0x03) -> Numerical
                param_id = 0x03
                var_name = "axle"
                field_label = "Axle Count"
                conv_type = "numerical"
                num_val = int.from_bytes(data_bytes, byteorder="big") if data_bytes else 0
                decoded_val = str(num_val)

            elif tag_byte in (0x44, 0x04):  # Registration Number (0x04) -> Alphanumeric
                param_id = 0x04
                var_name = "registration"
                field_label = "Registration No."
                conv_type = "alphanumeric"
                decoded_val = data_bytes.rstrip(b"\x00\x20\r\n ").decode("ascii", errors="ignore")
                if len(decoded_val) > 12:
                    decoded_val = decoded_val[:12]

            elif tag_byte in (0x45, 0x05):  # Gross Weight (0x05) -> Decimal
                param_id = 0x05
                var_name = "gvw"
                field_label = "GVW/GCW"
                conv_type = "decimal"
                raw_weight = int.from_bytes(data_bytes, byteorder="big") if data_bytes else 0
                decoded_val = str(raw_weight)

            elif tag_byte in (0x46, 0x06):  # Meta Data / TA Cert (0x06) -> Hex As-Is
                param_id = 0x06
                var_name = "cert"
                field_label = "TA Certification"
                conv_type = "hex as it is"
                decoded_val = data_bytes.hex().upper()

            elif tag_byte in (0x47, 0x07, 0x63):  # Release Version (some firmware tags this as 0x63, not 0x47)
                param_id = 0x07
                var_name = "rel_version"
                field_label = "Rel Version"
                conv_type = "alphanumeric"
                try:
                    decoded_val = data_bytes.decode("ascii", errors="ignore").strip()
                    decoded_val = normalize_rel_version_value(decoded_val)
                    if not decoded_val:
                        decoded_val = data_bytes.hex().upper()
                except Exception:
                    decoded_val = data_bytes.hex().upper()

            if var_name:
                if param_id in self.tag_form_comp.pending_requests:
                    # Retrieve matching command_sent hex from pending_requests
                    pending_info = self.tag_form_comp.pending_requests.pop(param_id)
                    cmd_sent = pending_info.get("Command Sent", "")
                    op_type = pending_info.get("Operation", "Read")
                    on_success_cb = pending_info.get("on_success")

                    clean_value = decoded_val.strip()
                    is_no_data = not clean_value or not clean_value.strip("0")
                    if op_type == "Read" and is_no_data:
                        self.tag_form_comp.set_field_value(var_name, "")
                        self.comm_panel_comp.show_fail(description="No ID/data found")
                        write_log(
                            f"{medium} RX ({field_label}): No ID/data found [Response: {payload_hex_spaced}]",
                            log_console,
                        )
                        log_console.append_json(
                            name=field_label,
                            operation=op_type,
                            command_sent=cmd_sent,
                            response_received=frame_hex,
                            conversion=conv_type,
                            medium=medium,
                        )

                        on_failure_cb = pending_info.get("on_failure")
                        if callable(on_failure_cb):
                            try:
                                on_failure_cb("NO_DATA")
                            except Exception:
                                pass
                        return

                    # 1. Update UI Entry Box immediately
                    self.tag_form_comp.set_field_value(var_name, decoded_val)

                    # 2. Display PASS Card with decoded positive response matching the input field
                    self.comm_panel_comp.show_pass(decoded_val)

                    # 3. Log clean text line in console window
                    write_log(f"{medium} RX ({field_label}): {decoded_val} [Response: {payload_hex_spaced}]", log_console)

                    # 4. Save SINGLE completed JSON entry with BOTH Command Sent and Response Received
                    log_console.append_json(
                        name=field_label,
                        operation=op_type,
                        command_sent=cmd_sent,
                        response_received=frame_hex,
                        conversion=conv_type,
                        medium=medium,
                    )

                    if callable(on_success_cb):
                        try:
                            on_success_cb(decoded_val)
                        except Exception:
                            pass
                else:
                    # Late response arrived after 5-second timeout -> ignore and preserve NO RESPONSE status
                    write_log(
                        f"UART RX Ignored (Late response received after timeout for {field_label}): [Payload: {payload_hex_spaced}]",
                        log_console,
                    )

        except Exception as e:
            self.comm_panel_comp.show_fail(description=str(e))
            write_log(f"Error parsing response frame: {e}", log_console)

    def update_gui(self):
        """Optimized GUI event loop extracting frames strictly using expected length and trailer '#'."""
        batch = self.reader.get_raw_batch(max_items=30)
        for raw in batch:
            self.rx_buffer.extend(raw)

        # Buffer cap protection
        if len(self.rx_buffer) > 8192:
            del self.rx_buffer[:-2048]

        while len(self.rx_buffer) >= 5:
            # Drop any leading garbage before '$' (0x24) if '$' exists
            if 0x24 in self.rx_buffer:
                start_idx = self.rx_buffer.index(0x24)
                if start_idx > 0:
                    del self.rx_buffer[:start_idx]

            # Case A: Full Binary Frame starting with '$' (0x24)
            if len(self.rx_buffer) >= 5 and self.rx_buffer[0] == 0x24:
                length_byte = self.rx_buffer[2]
                frame_found = False

                # Candidate expected lengths based on length_byte:
                # 1) length_byte includes TAG + PAYLOAD + CRC (e.g. 24 EF <LEN> 40 <DATA> <CRC> 23 -> LEN + 4)
                # 2) length_byte includes CMD + FIELD_ID + PAYLOAD (followed by 2 CRC bytes + 23 -> LEN + 6)
                # 3) length_byte is exact PAYLOAD length (e.g. 24 EF <LEN> 40 <DATA> <CRC> 23 -> LEN + 6 or LEN + 7)
                # 4) length_byte is exact PAYLOAD length without CRC (e.g. 24 EF <LEN> 40 <DATA> 23 -> LEN + 4 or LEN + 5)
                candidate_lengths = [
                    length_byte + 4,
                    length_byte + 6,
                    length_byte + 5,
                    length_byte + 7,
                ]

                for exp_len in candidate_lengths:
                    if exp_len >= 5 and len(self.rx_buffer) >= exp_len:
                        if self.rx_buffer[exp_len - 1] == 0x23:
                            frame = bytes(self.rx_buffer[:exp_len])
                            del self.rx_buffer[:exp_len]
                            self._parse_uart_response(frame)
                            frame_found = True
                            break

                if frame_found:
                    continue

                # If minimum candidate length has not arrived yet, wait for remaining bytes
                min_exp = min(candidate_lengths) if candidate_lengths else 5
                if len(self.rx_buffer) < min_exp:
                    break

                # If buffer has accumulated past max expected length and no trailer matched at expected positions:
                max_exp = max(candidate_lengths) if candidate_lengths else 50
                if len(self.rx_buffer) > max_exp:
                    # Check if there is another '$' downstream to resync
                    try:
                        next_start = self.rx_buffer.index(0x24, 1)
                        del self.rx_buffer[:next_start]
                        continue
                    except ValueError:
                        # Fallback to finding next 0x23 to discard invalid chunk
                        try:
                            end_idx = self.rx_buffer.index(0x23)
                            del self.rx_buffer[:end_idx + 1]
                            continue
                        except ValueError:
                            break
                else:
                    break

            # Case B: ASCII hex text string frame (e.g. b"24EF...23" or b"0469...23")
            elif (len(self.rx_buffer) >= 4 and (self.rx_buffer[:2] == b"24" or self.rx_buffer[:2] == b"EF")) or (b"24" in self.rx_buffer or b"EF" in self.rx_buffer):
                try:
                    end_idx = self.rx_buffer.index(0x23)  # Find '#'
                except ValueError:
                    break
                raw_chunk = bytes(self.rx_buffer[: end_idx + 1])
                del self.rx_buffer[: end_idx + 1]
                try:
                    ascii_str = raw_chunk.decode("ascii", errors="ignore").replace(" ", "").strip()
                    raw_binary_frame = bytes.fromhex(ascii_str)
                    if len(raw_binary_frame) >= 5:
                        self._parse_uart_response(raw_binary_frame)
                except Exception:
                    pass

            # Case C: Direct Compact Binary Frame without '$' (e.g. 04 69 03 00 14 25 80 23)
            elif len(self.rx_buffer) >= 5:
                length_byte = self.rx_buffer[0]
                frame_found = False
                candidate_lengths = [length_byte + 1, length_byte + 2, length_byte + 3, length_byte + 4]

                for exp_len in candidate_lengths:
                    if exp_len >= 5 and len(self.rx_buffer) >= exp_len:
                        if self.rx_buffer[exp_len - 1] == 0x23:
                            frame = bytes(self.rx_buffer[:exp_len])
                            del self.rx_buffer[:exp_len]
                            self._parse_uart_response(frame)
                            frame_found = True
                            break

                if frame_found:
                    continue

                try:
                    end_idx = self.rx_buffer.index(0x23)
                    frame = bytes(self.rx_buffer[: end_idx + 1])
                    del self.rx_buffer[: end_idx + 1]
                    self._parse_uart_response(frame)
                except ValueError:
                    break
            else:
                break

        self.root.after(50, self.update_gui)

    def on_close(self):
        try:
            self.reader.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


def create_app() -> ttkb.Window:
    app = RFIDApp()
    return app.root
