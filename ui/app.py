from pathlib import Path
import ttkbootstrap as ttkb

from config import PORT, BAUDRATE
from communication import SerialReader
from logger import write_log
from ui.components.header import build_header_frame
from ui.components.tag_form import TagFormFrame
from ui.components.comm_panel import CommPanelFrame
from ui.components.log_panel import LogPanelFrame


class RFIDApp:
    """Main Application orchestrator for RFID Communicator UI."""

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent

        self.root = ttkb.Window(themename="cyborg")
        # self.root.title("Disable Maximize")
        self.root.geometry("1300x750")
        # self.root.resizable(False, False)
        self.root.minsize(1200, 750)
        self.root.title("RFID Tag Reader & Writer")

        self._configure_styles()
        self._set_app_icon()

        self.reader = SerialReader(PORT, BAUDRATE)
        self.logging_enabled = False
        self.rx_buffer = bytearray()

        self.main_frame = ttkb.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.header_frame = build_header_frame(self.main_frame, self.base_dir)

        self.content_frame = ttkb.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.top_row = ttkb.Frame(self.content_frame)
        self.top_row.pack(fill="x", expand=False, pady=(0, 12))

        # Log panel component
        self.log_panel_comp = LogPanelFrame(self.content_frame, self.root)

        # Tag form component
        self.tag_form_comp = TagFormFrame(
            self.top_row,
            self.root,
            self.reader,
            lambda: self.log_panel_comp.log_console,
            reset_reader_status_cb=None,
            timeout_cb=self._on_command_timeout,
        )

        # Comm panel component
        self.comm_panel_comp = CommPanelFrame(
            self.top_row,
            self.reader,
            lambda: self.log_panel_comp.log_console,
            self._on_connection_change,
            diagnostic_parent=self.content_frame,
        )

        self._bind_events()
        self.root.after(50, self.update_gui)

    def _configure_styles(self):
        style = ttkb.Style(theme="cyborg")
        style.configure("Card.TFrame", background="#1f2937")
        style.configure("Header.TFrame", background="#111827")
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground="#F8FAFC")
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground="#E2E8F0")
        style.configure("Field.TLabel", font=("Segoe UI", 10), foreground="#E2E8F0")
        style.configure("Caption.TLabel", font=("Segoe UI", 9), foreground="#94a3b8")

        # Rounded styling for Entry boxes, Buttons, and Comboboxes
        style.configure("TEntry", padding=(8, 6), borderwidth=1, relief="flat")
        style.configure("TButton", padding=(10, 6), borderwidth=1, relief="flat")
        style.configure("TCombobox", padding=(6, 5))

    def _on_command_timeout(self, field_label: str):
        if field_label == "Tag ID":
            self.tag_form_comp.clear_field_value("tag_id")
            self.comm_panel_comp.show_no_tag_found()
        else:
            self.comm_panel_comp.show_timeout(field_label)
        self.tag_form_comp.show_response(
            f"No reply from reader for {field_label}.",
            success=False,
        )

    def _set_app_icon(self):
        icon_path = self.base_dir / "assets" / "Acc_logo.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

    def _on_connection_change(self, connected: bool):
        if not connected:
            self.comm_panel_comp.show_disconnected()

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
        """Universal parser for UART response frames starting with 24EF and ending with 23."""
        log_console = self.log_panel_comp.log_console
        medium = self.comm_panel_comp.medium_var.get()
        frame_hex = frame.hex().upper()

        try:
            if len(frame) < 5:
                self.comm_panel_comp.show_fail(description="Frame too short")
                self.tag_form_comp.show_response("Frame too short", success=False)
                return

            tag_byte = frame[3]  # Response Tag / Command ID Byte

            # Negative response check (0x7F when length == 3 or error format)
            if tag_byte == 0x7F and len(frame) <= 8 and len(frame[4:-3]) <= 2:
                failed_cmd = frame[4] if len(frame) > 4 else 0
                error_code = frame[5] if len(frame) > 5 else 0x01
                if failed_cmd in self.tag_form_comp.pending_requests:
                    self.tag_form_comp.pending_requests.pop(failed_cmd)
                    self.comm_panel_comp.show_fail(error_code=error_code)
                    self.tag_form_comp.show_response(
                        f"Error 0x{error_code:02X}", success=False
                    )
                    write_log(f"UART RX Negative Response for Cmd 0x{failed_cmd:02X} (Error 0x{error_code:02X})", log_console)
                    log_console.append_json(
                        name=f"Cmd 0x{failed_cmd:02X}",
                        operation="Negative Response",
                        command_sent="",
                        response_received=frame_hex,
                        conversion="error",
                        medium=medium,
                    )
                else:
                    write_log(f"UART RX Ignored (Late Negative Response after timeout for Cmd 0x{failed_cmd:02X})", log_console)
                return
            # ------------------------------
# Positive Write Response
# ------------------------------

    #         if tag_byte != 0x7F:

    # # Any pending write request?
    #             for param_id, pending_info in list(self.tag_form_comp.pending_requests.items()):

    #                 if pending_info.get("Operation") == "Write":

    #                     self.tag_form_comp.pending_requests.pop(param_id)

    #                     self.comm_panel_comp.show_pass("PASS")

    #                     write_log(
    #             f"Write Successful : {pending_info.get('Name','')}",
    #             log_console,
    #         )

    #                     log_console.append_json(
        
    #                         name=pending_info.get("Name", ""),
    #                         operation="Write",
    #                         command_sent=pending_info.get("Command Sent", ""),
    #                         response_received=frame.hex().upper(),
    #                         conversion="PASS",
    #                         medium=medium,
    #         )

    #         return
            # Positive Response Payload extraction (using length byte if available)
            length_byte = frame[2] if len(frame) > 2 else 0
            if length_byte > 0:
                if length_byte == len(frame) - 4:
                    payload_len = max(0, length_byte - 3)
                elif length_byte == len(frame) - 6:
                    payload_len = max(0, length_byte - 1)
                elif length_byte <= (len(frame) - 5):
                    payload_len = length_byte
                else:
                    payload_len = max(0, len(frame) - 7) if len(frame) >= 7 else max(0, len(frame) - 5)
                data_bytes = frame[4 : 4 + payload_len]
            else:
                data_bytes = frame[4:-3] if len(frame) >= 7 else frame[4:-1]

            payload_hex_spaced = data_bytes.hex(" ").upper()

            var_name = ""
            field_label = ""
            conv_type = ""
            decoded_val = ""
            param_id = None

            if tag_byte == 0x40:  # Tag EPC (0x00) -> Hex As-Is
                param_id = 0x00
                var_name = "tag_id"
                field_label = "Tag ID"
                conv_type = "hex as it is"
                decoded_val = data_bytes.hex().upper()
                if len(decoded_val) > 24:
                    decoded_val = decoded_val[:24]

            elif tag_byte == 0x41:  # Serial Reader Number (0x01) -> Alphanumeric
                param_id = 0x01
                var_name = "serial"
                field_label = "Serial Number"
                conv_type = "alphanumeric"
                decoded_val = data_bytes.decode("ascii", errors="ignore").rstrip("\x00").strip()

            elif tag_byte == 0x42:  # Trailer VIN (0x02) -> Alphanumeric
                param_id = 0x02
                var_name = "vin"
                field_label = "VIN"
                conv_type = "alphanumeric"
                decoded_val = data_bytes.decode("ascii", errors="ignore").rstrip("\x00").strip()

            elif tag_byte == 0x43:  # Axle Count (0x03) -> Numerical
                param_id = 0x03
                var_name = "axle"
                field_label = "Axle Count"
                conv_type = "numerical"
                num_val = int.from_bytes(data_bytes, byteorder="big") if data_bytes else 0
                decoded_val = str(num_val)

            elif tag_byte == 0x44:  # Registration Number (0x04) -> Alphanumeric
                param_id = 0x04
                var_name = "registration"
                field_label = "Registration No."
                conv_type = "alphanumeric"
                decoded_val = data_bytes.decode("ascii", errors="ignore").rstrip("\x00").strip()

            elif tag_byte == 0x45:  # Gross Weight (0x05) -> Decimal
                param_id = 0x05
                var_name = "gvw"
                field_label = "GVW/GCW"
                conv_type = "decimal"
                weight_val = int.from_bytes(data_bytes, byteorder="big") if data_bytes else 0
                decoded_val = str(weight_val)

            elif tag_byte in (0x46, 0x7F):  # Meta Data / TA Cert (0x06) -> Hex As-Is
                param_id = 0x06
                var_name = "cert"
                field_label = "TA Certification"
                conv_type = "hex as it is"
                decoded_val = data_bytes.hex().upper()

            if var_name:
                if param_id in self.tag_form_comp.pending_requests:
                    # Retrieve matching command_sent hex from pending_requests
                    pending_info = self.tag_form_comp.pending_requests.pop(param_id)
                    cmd_sent = pending_info.get("Command Sent", "")
                    op_type = pending_info.get("Operation", "Read")

                    if var_name == "tag_id" and data_bytes and not any(data_bytes):
                        self.tag_form_comp.clear_field_value("tag_id")
                        self.comm_panel_comp.show_no_tag_found()
                        self.tag_form_comp.show_response(
                            "No reply from reader for Tag ID.",
                            success=False,
                        )
                        write_log("UART RX: No Tag Found", log_console)
                        return

                    # 1. Update UI Entry Box immediately
                    self.tag_form_comp.set_field_value(var_name, decoded_val)

                    # 2. Keep both response displays identical to the decoded field value
                    self.comm_panel_comp.show_pass(decoded_val)
                    self.tag_form_comp.show_response(decoded_val)

                    # 3. Log clean text line in console window
                    write_log(f"UART RX ({field_label}): {decoded_val} [Payload: {payload_hex_spaced}]", log_console)

                    # 4. Save SINGLE completed JSON entry with BOTH Command Sent and Response Received
                    log_console.append_json(
                        name=field_label,
                        operation=op_type,
                        command_sent=cmd_sent,
                        response_received=frame_hex,
                        conversion=conv_type,
                        medium=medium,
                    )
                    if op_type == "Read":
                        log_console.append_csv(
                            name=field_label,
                            operation=op_type,
                            command_sent=cmd_sent,
                            response_received=decoded_val,
                            conversion=conv_type,
                            medium=medium,
                        )
                # else:
                #     # Late response arrived after 5-second timeout -> ignore and preserve NO RESPONSE status
                #     write_log(
                #         f"UART RX Ignored (Late response received after timeout for {field_label}): [Payload: {payload_hex_spaced}]",
                #         log_console,
                #     )

        except Exception as e:
            self.comm_panel_comp.show_fail(description=str(e))
            self.tag_form_comp.show_response(str(e), success=False)
            write_log(f"Error parsing response frame: {e}", log_console)

    def update_gui(self):
        """Optimized GUI event loop processing both raw binary and ASCII hex UART packet batches."""
        batch = self.reader.get_raw_batch(max_items=30)
        for raw in batch:
            self.rx_buffer.extend(raw)

        # Buffer cap protection
        if len(self.rx_buffer) > 8192:
            del self.rx_buffer[:-2048]

        # Parse framed UART packets ($ ... # or 24 ... 23 ASCII)
        while True:
            # 1. Check for raw binary frame start (0x24 = '$')
            try:
                start_bin = self.rx_buffer.index(0x24)
            except ValueError:
                start_bin = -1

            # 2. Check for ASCII text frame start ('2' '4' = b"24")
            try:
                start_asc = self.rx_buffer.find(b"24EF")
            except ValueError:
                start_asc = -1

            if start_bin == -1 and start_asc == -1:
                self.rx_buffer.clear()
                break

            # Handle Binary Frame
            if start_bin != -1 and (start_asc == -1 or start_bin <= start_asc):
                if start_bin > 0:
                    del self.rx_buffer[:start_bin]

                if len(self.rx_buffer) < 5:
                    break

                length_byte = self.rx_buffer[2]
                frame_found = False

                # Candidate expected lengths based on length_byte:
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
                            if frame.startswith(b"\x24\xEF"):
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
                    try:
                        next_start = self.rx_buffer.index(0x24, 1)
                        del self.rx_buffer[:next_start]
                        continue
                    except ValueError:
                        del self.rx_buffer[0]
                        break
                else:
                    break

            # Handle ASCII Frame
            elif start_asc != -1:
                if start_asc > 0:
                    del self.rx_buffer[:start_asc]

                try:
                    end_asc = self.rx_buffer.find(b"23", 2)
                except ValueError:
                    if len(self.rx_buffer) > 512:
                        del self.rx_buffer[0]
                    break

                if end_asc == -1:
                    break

                ascii_bytes = bytes(self.rx_buffer[: end_asc + 2])
                del self.rx_buffer[: end_asc + 2]

                try:
                    ascii_str = ascii_bytes.decode("ascii", errors="ignore").replace(" ", "").strip()
                    raw_binary_frame = bytes.fromhex(ascii_str)
                    if raw_binary_frame.startswith(b"\x24\xEF"):
                        self._parse_uart_response(raw_binary_frame)
                except Exception:
                    pass

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
