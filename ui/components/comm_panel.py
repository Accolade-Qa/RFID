import threading
import tkinter as tk
import ttkbootstrap as ttkb
from serial.tools import list_ports
from config import PORT, BAUDRATE, ERROR_CODES
from logger import write_log

UART_BAUD_RATES = ["9600", "19200", "38400", "57600", "115200"]


def detect_com_ports():
    try:
        ports = [port.device for port in list_ports.comports()]
        return sorted(ports)
    except Exception:
        return []


class CommPanelFrame:
    """Component managing UART communication settings and diagnostic result cards."""

    def __init__(self, parent_frame, reader, log_console_getter, on_connection_change_cb):
        self.reader = reader
        self.get_log_console = log_console_getter
        self.on_connection_change_cb = on_connection_change_cb

        if hasattr(self.reader, "set_disconnect_callback"):
            self.reader.set_disconnect_callback(self._on_async_disconnect)

        # Main horizontal container holding Communication & Diagnostic Panel
        self.container_frame = ttkb.Frame(parent_frame)
        self.container_frame.pack(fill="x", expand=True)

        # Communication Settings Frame
        self.communication_frame = tk.LabelFrame(
            self.container_frame,
            text="Communication Settings",
            padx=14,
            pady=12,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        )
        self.communication_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Diagnostic Result Section
        self.diag_frame = tk.LabelFrame(
            self.container_frame,
            text="Diagnostic Results",
            padx=14,
            pady=12,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        )
        self.diag_frame.pack(side="left", fill="both", expand=True, padx=(0, 0))

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
        self.port_combobox = None
        self.baud_combobox = None

        fields = [
            ("COM Port", self.port_var, available_ports),
            ("Baud Rate", self.baud_var, UART_BAUD_RATES),
        ]

        for idx, (label_text, variable, values) in enumerate(fields):
            row = 0
            col = idx * 2

            ttkb.Label(self.communication_frame, text=label_text, style="Field.TLabel").grid(
                row=row, column=col, sticky="w", pady=(0, 6), padx=(0, 4)
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
            combobox.grid(row=row, column=col + 1, sticky="w", padx=(4, 10), pady=(0, 6))

            if label_text == "COM Port":
                self.port_combobox = combobox
            elif label_text == "Baud Rate":
                self.baud_combobox = combobox

        button_frame_comm = ttkb.Frame(self.communication_frame)
        button_frame_comm.grid(row=1, column=0, columnspan=4, pady=(8, 0), sticky="ew")

        self.connect_button = ttkb.Button(
            button_frame_comm,
            text="Connect",
            command=self.connect_reader,
            # pyrefly: ignore [unexpected-keyword]
            bootstyle="success",
            width=11,
        )
        self.connect_button.pack(side="left", padx=(0, 8))

        self.disconnect_button = ttkb.Button(
            button_frame_comm,
            text="Disconnect",
            command=self.disconnect_reader,
            # pyrefly: ignore [unexpected-keyword]
            bootstyle="danger",
            state="disabled",
            width=11,
        )
        self.disconnect_button.pack(side="left", padx=(0, 8))

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

        # Canvas icon
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
            wraplength=420,
        )
        self.subtext_label.pack(fill="x", anchor="w", pady=(2, 0))

    def draw_icon(self, status_type: str):
        self.icon_canvas.delete("all")
        if status_type == "disconnected":
            self.icon_canvas.create_oval(6, 6, 42, 42, outline="#6B7280", width=3)
            self.icon_canvas.create_oval(22, 22, 26, 26, fill="#6B7280", outline="")
        elif status_type == "connected":
            self.icon_canvas.create_oval(6, 6, 42, 42, outline="#10B981", width=3)
            self.icon_canvas.create_oval(20, 20, 28, 28, fill="#10B981", outline="")
        elif status_type == "pass":
            self.icon_canvas.create_oval(6, 6, 42, 42, outline="#10B981", width=3)
            self.icon_canvas.create_line(16, 24, 22, 30, 32, 18, fill="#10B981", width=3, capstyle="round", joinstyle="round")
        elif status_type == "fail":
            self.icon_canvas.create_oval(6, 6, 42, 42, outline="#EF4444", width=3)
            self.icon_canvas.create_line(18, 18, 30, 30, fill="#EF4444", width=3, capstyle="round")
            self.icon_canvas.create_line(30, 18, 18, 30, fill="#EF4444", width=3, capstyle="round")

    def _set_comm_controls_state(self, connected: bool):
        """Block port and baud controls when connected; enable when disconnected."""
        state = "disabled" if connected else "readonly"
        if hasattr(self, "port_combobox") and self.port_combobox:
            self.port_combobox.configure(state=state)
        if hasattr(self, "baud_combobox") and self.baud_combobox:
            self.baud_combobox.configure(state=state)

    def show_disconnected(self):
        self._set_comm_controls_state(False)
        self.accent_bar.configure(bg="#4B5563")
        self.draw_icon("disconnected")
        self.title_label.configure(text="Disconnected", fg="#9CA3AF")
        self.subtext_label.configure(text="Connect a serial port to continue.", fg="#9CA3AF")

    def show_connected(self, port: str = "", baud: int = 115200):
        self._set_comm_controls_state(True)
        self.accent_bar.configure(bg="#10B981")  # Emerald green
        self.draw_icon("connected")
        self.title_label.configure(text="Connected", fg="#10B981")
        self.subtext_label.configure(
            text=f"Serial port: {port} @ {baud} Baud | Ready for transmission.",
            fg="#E2E8F0",
        )

    def show_pass(self, value_text: str):
        self.accent_bar.configure(bg="#10B981")
        self.draw_icon("pass")
        self.title_label.configure(text="PASS", fg="#10B981")
        clean_val = str(value_text).strip()
        self.subtext_label.configure(
            text=f"Positive response: {clean_val}",
            fg="#E2E8F0",
        )

    def show_fail(self, error_code: int = None, description: str = ""):
        self.accent_bar.configure(bg="#EF4444")
        self.draw_icon("fail")
        self.title_label.configure(text="FAIL", fg="#EF4444")

        if error_code is not None:
            err_desc = ERROR_CODES.get(error_code, f"Unknown Error Code 0x{error_code:02X}")
            sub = f"Error 0x{error_code:02X}: {err_desc}"
        elif description:
            sub = f"Failure: {description}"
        else:
            sub = "Negative response or CRC verification error."

        self.subtext_label.configure(text=sub, fg="#FCA5A5")

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

        self._set_comm_controls_state(True)
        self.title_label.configure(text="Connecting...", fg="#FBBF24")
        self.subtext_label.configure(text=f"Opening {selected_port} @ {selected_baud} via UART...", fg="#FBBF24")
        self.accent_bar.configure(bg="#FBBF24")
        self.connect_button.configure(state="disabled")

        def _do_connect():
            success = self.reader.connect(
                port_or_channel=selected_port,
                baud_or_bitrate=selected_baud,
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
            self._set_comm_controls_state(True)
            self.connect_button.configure(state="disabled")
            self.disconnect_button.configure(state="normal")
            self.show_connected(port, baud)
            write_log(f"Connected to {port} @ {baud} via UART", log_console)
            if callable(self.on_connection_change_cb):
                self.on_connection_change_cb(True)
        else:
            self._set_comm_controls_state(False)
            self.show_disconnected()
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")
            write_log(f"Failed to connect to {port} via UART", log_console)
            if callable(self.on_connection_change_cb):
                self.on_connection_change_cb(False)

    def _on_async_disconnect(self):
        try:
            self.container_frame.after(0, self._process_async_disconnect)
        except Exception:
            pass

    def _process_async_disconnect(self):
        if hasattr(self, "disconnect_button") and str(self.disconnect_button.cget("state")) == "disabled":
            return

        self._set_comm_controls_state(False)
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
