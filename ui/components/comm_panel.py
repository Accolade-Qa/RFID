import threading
import tkinter as tk
import ttkbootstrap as ttkb
from serial.tools import list_ports
from config import PORT, BAUDRATE
from logger import write_log

# Negative Response Error Codes (VLTD Protocol Spec)
ERROR_CODES = {
    0x00: "AEPL_RFID_RESULT_OK: Request processed successfully.",
    0x01: "AEPL_RFID_RESULT_INVALID_PARAMETER: Invalid or NULL input parameter.",
    0x02: "AEPL_RFID_RESULT_INVALID_FRAME: Invalid or malformed request frame.",
    0x03: "AEPL_RFID_RESULT_INVALID_ECU_ID: Unsupported or incorrect ECU ID.",
    0x04: "AEPL_RFID_RESULT_INVALID_LENGTH: Frame length does not match expected value.",
    0x05: "AEPL_RFID_RESULT_CRC_ERROR: CRC verification failed.",
    0x06: "AEPL_RFID_RESULT_UNSUPPORTED_COMMAND: Requested Command ID is not supported.",
    0x07: "AEPL_RFID_RESULT_DATA_UNAVAILABLE: Requested parameter is unavailable.",
    0x08: "AEPL_RFID_RESULT_TX_FAILED: Failed to transmit response frame.",
}


def detect_com_ports():
    try:
        ports = [port.device for port in list_ports.comports()]
        return sorted(ports)
    except Exception:
        return []


class CommPanelFrame:
    """Component managing serial communication settings and screenshot-matched Diagnostic Result Cards."""

    def __init__(self, parent_frame, reader, log_console_getter, on_connection_change_cb, diagnostic_parent=None):
        self.reader = reader
        self.get_log_console = log_console_getter
        self.on_connection_change_cb = on_connection_change_cb

        self.reader.set_disconnect_callback(self._on_async_disconnect)

        # The communication controls stay in the top row; diagnostics may be
        # placed in a separate full-width row by the application layout.
        self.container_frame = ttkb.Frame(parent_frame)
        self.container_frame.pack(side="left", fill="both", expand=True, padx=(0, 0))

        # Communication Settings Frame
        self.communication_frame = tk.LabelFrame(
            self.container_frame,
            text="Communication Settings",
            padx=14,
            pady=10,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        )
        self.communication_frame.pack(side="top", fill="both", expand=True, padx=(0, 0))

        # Diagnostic Result Section (Matching Screenshots)
        self.diag_frame = tk.LabelFrame(
            diagnostic_parent or self.container_frame,
            text="Diagnostic Results",
            padx=14,
            pady=12,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        )
        self.diag_frame.pack(side="top", fill="both", expand=True, padx=(0, 0))

        self.medium_var = tk.StringVar(value="UART")
        self.baud_var = tk.StringVar(value=str(BAUDRATE))

        ports = detect_com_ports()
        if not ports:
            ports = ["COM1", "COM2", "COM3", "COM4", "COM5"]
        default_port = PORT if PORT in ports else ports[0]
        self.port_var = tk.StringVar(value=default_port)

        self._build_comm_widgets(ports)
        self._build_diag_card()
        self.show_disconnected()

    def _build_comm_widgets(self, available_ports):
        available_baud_rates = ["9600", "19200", "38400", "57600", "115200"]
        self.port_combobox = None

        fields = [
            ("Medium", self.medium_var, ["UART", "CAN"]),
            ("COM Port", self.port_var, available_ports),
            ("Baud Rate", self.baud_var, available_baud_rates),
        ]

        field_positions = {
            "Medium": (0, 0),
            "COM Port": (0, 2),
            "Baud Rate": (2, 0),
        }

        self.communication_frame.columnconfigure(0, weight=1)
        self.communication_frame.columnconfigure(2, weight=1)

        for label_text, variable, values in fields:
            row, col = field_positions[label_text]

            label_pady = (0, 8) if label_text != "Baud Rate" else (12, 8)
            combo_pady = (0, 8) if label_text != "Baud Rate" else (0, 16)
            combo_padx = (0, 22) if label_text == "Medium" else (0, 10)

            ttkb.Label(self.communication_frame, text=label_text, style="Field.TLabel").grid(
                row=row, column=col, sticky="w", pady=label_pady, padx=(0, 4)
            )
            combobox = ttkb.Combobox(
                self.communication_frame,
                textvariable=variable,
                values=values,
                state="readonly",
                # pyrefly: ignore [unexpected-keyword]
                bootstyle="info",
                width=13,
            )
            combobox.grid(row=row + 1, column=col, sticky="ew", padx=combo_padx, pady=combo_pady)
            if label_text == "COM Port":
                self.port_combobox = combobox

        button_frame_comm = ttkb.Frame(self.communication_frame)
        button_frame_comm.grid(row=4, column=0, columnspan=4, pady=(12, 0), sticky="w")

        self.connect_button = ttkb.Button(
            button_frame_comm,
            text="Connect",
            command=self.connect_reader,
            # pyrefly: ignore [unexpected-keyword]
            bootstyle="success",
            width=11,
        )
        self.connect_button.pack(side="left", padx=(0, 20))

        self.disconnect_button = ttkb.Button(
            button_frame_comm,
            text="Disconnect",
            command=self.disconnect_reader,
            # pyrefly: ignore [unexpected-keyword]
            bootstyle="danger",
            state="disabled",
            width=11,
        )
        self.disconnect_button.pack(side="left")

    def _build_diag_card(self):
        """Build Card UI for Disconnected / Connected / PASS / FAIL results."""
        self.card_container = tk.Frame(
            self.diag_frame,
            bg="#111827",
            highlightthickness=1,
            highlightbackground="#374151",
        )
        self.card_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Left Vertical Accent Bar
        self.accent_bar = tk.Frame(self.card_container, bg="#4B5563", width=5)
        self.accent_bar.pack(side="left", fill="y", padx=(0, 12))

        # Canvas icon (circular icon)
        self.icon_canvas = tk.Canvas(
            self.card_container,
            width=48,
            height=48,
            bg="#111827",
            highlightthickness=0,
        )
        self.icon_canvas.pack(side="left", padx=(0, 12), pady=10)

        # Right Text Box (Title + Subtext)
        self.text_frame = tk.Frame(self.card_container, bg="#111827")
        self.text_frame.pack(side="left", fill="both", expand=True, pady=8)

        self.title_label = tk.Label(
            self.text_frame,
            text="Disconnected",
            font=("Segoe UI", 15, "bold"),
            fg="#9CA3AF",
            bg="#111827",
            anchor="w",
        )
        self.title_label.pack(fill="x", anchor="w")

        self.subtext_label = tk.Label(
            self.text_frame,
            text="Connect a port to continue.",
            font=("Segoe UI", 10),
            fg="#9CA3AF",
            bg="#111827",
            anchor="w",
            justify="left",
            wraplength=0,
        )
        self.subtext_label.pack(fill="x", anchor="w", pady=(2, 0))

    def draw_icon(self, status_type: str):
        self.icon_canvas.delete("all")
        if status_type == "disconnected":
            # Outer gray circle + inner dot
            self.icon_canvas.create_oval(6, 6, 42, 42, outline="#6B7280", width=3)
            self.icon_canvas.create_oval(22, 22, 26, 26, fill="#6B7280", outline="")
        elif status_type == "connected":
            # Outer green circle + inner green dot
            self.icon_canvas.create_oval(6, 6, 42, 42, outline="#10B981", width=3)
            self.icon_canvas.create_oval(20, 20, 28, 28, fill="#10B981", outline="")
        elif status_type == "pass":
            # Outer green circle + checkmark
            self.icon_canvas.create_oval(6, 6, 42, 42, outline="#10B981", width=3)
            self.icon_canvas.create_line(16, 24, 22, 30, 32, 18, fill="#10B981", width=3, capstyle="round", joinstyle="round")
        elif status_type == "fail":
            # Outer red circle + cross
            self.icon_canvas.create_oval(6, 6, 42, 42, outline="#EF4444", width=3)
            self.icon_canvas.create_line(18, 18, 30, 30, fill="#EF4444", width=3, capstyle="round")
            self.icon_canvas.create_line(30, 18, 18, 30, fill="#EF4444", width=3, capstyle="round")

    def show_disconnected(self):
        self.accent_bar.configure(bg="#4B5563")
        self.draw_icon("disconnected")
        self.title_label.configure(text="Disconnected", fg="#9CA3AF")
        self.subtext_label.configure(text="Connect a port to continue.", fg="#9CA3AF")

    def show_connected(self, port: str = "", baud: int = 115200):
        self.accent_bar.configure(bg="#10B981")  # Emerald green
        self.draw_icon("connected")
        self.title_label.configure(text="Connected", fg="#10B981")
        self.subtext_label.configure(
            text=f"Port: {port} @ {baud} Baud | Ready for transmission.",
            fg="#E2E8F0",
        )

    def show_pass(self, payload_hex: str):
        self.accent_bar.configure(bg="#10B981")
        self.draw_icon("pass")
        self.title_label.configure(text="PASS", fg="#10B981")
        self.subtext_label.configure(
            text=f"Positive response: {payload_hex}",
            fg="#E2E8F0",
        )

    def show_fail(self, error_code: int = None, description: str = ""):
        self.accent_bar.configure(bg="#EF4444")
        self.draw_icon("fail")
        self.title_label.configure(text="FAIL", fg="#EF4444")
        
        if error_code is not None and error_code in ERROR_CODES:
            sub = f"Error 0x{error_code:02X}: {ERROR_CODES[error_code]}"
        elif description:
            sub = f"Failure: {description}"
        else:
            sub = "Negative response or CRC verification error."

        self.subtext_label.configure(text=sub, fg="#FCA5A5")

    def show_no_tag_found(self):
        self.accent_bar.configure(bg="#EF4444")
        self.draw_icon("fail")
        self.title_label.configure(text="FAIL", fg="#EF4444")
        self.subtext_label.configure(
            text="Negative Response: No Tag Found",
            fg="#FCA5A5",
        )

    def show_timeout(self, cmd_name: str = ""):
        self.accent_bar.configure(bg="#EF4444")
        self.draw_icon("fail")
        self.title_label.configure(text="NO RESPONSE", fg="#EF4444")
        sub = f"No reply from reader within 5 seconds for {cmd_name}." if cmd_name else "No reply from reader within 5 seconds."
        self.subtext_label.configure(text=sub, fg="#FCA5A5")

    def populate_com_ports(self):
        ports = detect_com_ports()
        if not ports:
            ports = ["COM1", "COM2", "COM3", "COM4", "COM5"]
        if self.port_combobox:
            self.port_combobox.configure(values=ports)
        if self.port_var.get() not in ports:
            self.port_var.set(ports[0])

    def connect_reader(self):
        log_console = self.get_log_console()
        if self.reader.is_connected():
            write_log("Reader already connected", log_console)
            return

        selected_port = self.port_var.get()
        try:
            selected_baud = int(self.baud_var.get())
        except ValueError:
            selected_baud = 115200

        self.title_label.configure(text="Connecting...", fg="#FBBF24")
        self.subtext_label.configure(text=f"Opening {selected_port} @ {selected_baud}...", fg="#FBBF24")
        self.accent_bar.configure(bg="#FBBF24")
        self.connect_button.configure(state="disabled")

        def _do_connect():
            success = self.reader.connect(
                port=selected_port,
                baudrate=selected_baud,
            )
            try:
                self.container_frame.after(
                    0, lambda: self._on_connect_finished(success, selected_port, selected_baud)
                )
            except Exception:
                pass

        threading.Thread(target=_do_connect, daemon=True).start()

    def _on_connect_finished(self, success: bool, port: str, baud: int):
        log_console = self.get_log_console()
        if success:
            self.connect_button.configure(state="disabled")
            self.disconnect_button.configure(state="normal")
            self.show_connected(port, baud)
            write_log(f"Connected to {port} @ {baud} via {self.medium_var.get()}", log_console)
            if callable(self.on_connection_change_cb):
                self.on_connection_change_cb(True)
        else:
            self.show_disconnected()
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")
            write_log(f"Failed to connect to {port}", log_console)
            if callable(self.on_connection_change_cb):
                self.on_connection_change_cb(False)

    def _on_async_disconnect(self):
        try:
            self.container_frame.after(0, self._process_async_disconnect)
        except Exception:
            pass

    def _process_async_disconnect(self):
        self.show_disconnected()
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        write_log("Reader connection lost or closed", self.get_log_console())
        if callable(self.on_connection_change_cb):
            self.on_connection_change_cb(False)

    def disconnect_reader(self):
        def _do_disconnect():
            self.reader.disconnect()
            try:
                self.container_frame.after(0, self._process_async_disconnect)
            except Exception:
                pass

        threading.Thread(target=_do_disconnect, daemon=True).start()
