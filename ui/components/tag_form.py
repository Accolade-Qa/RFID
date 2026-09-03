import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttkb

from validation import (
    TAG_ID_PLACEHOLDER,
    SERIAL_PLACEHOLDER,
    VIN_PLACEHOLDER,
    AXLE_PLACEHOLDER,
    GVW_PLACEHOLDER,
    REGISTRATION_PLACEHOLDER,
    validate_tag_id_entry,
    is_serial_valid,
    validate_serial_entry,
    is_vin_valid,
    validate_vin_entry,
    is_registration_valid,
    validate_registration_entry,
    is_integer_in_range,
    validate_numeric_range_entry,
)
from logger import write_log
from communication.protocol import build_write_transmission_frame

FIELD_ROWS = [
    ("Tag ID", "tag_id"),
    ("Serial Number", "serial"),
    ("TA Certification", "cert"),
    ("GVW/GCW", "gvw"),
    ("VIN", "vin"),
    ("Registration No.", "registration"),
    ("Axle Count", "axle"),
]

READ_COMMANDS = {
    "tag_id": ("24110100E1F023", "hex as it is", "Tag ID", 0x00),
    "serial": ("24110101F1D123", "alphanumeric", "Serial Number", 0x01),
    "vin": ("24110102C1B223", "alphanumeric", "VIN", 0x02),
    "axle": ("24110103D19323", "numerical", "Axle Count", 0x03),
    "registration": ("24110104A17423", "alphanumeric", "Registration No.", 0x04),
    "gvw": ("24110105B15523", "decimal", "GVW/GCW", 0x05),
    "cert": ("24110106813623", "hex as it is", "TA Certification", 0x06),
}

HIDDEN_FIELD_NAMES = {"serial", "cert", "gvw", "vin", "registration", "axle"}

AUTO_READ_FIELDS = ("tag_id", "serial", "vin", "axle", "registration", "gvw", "cert")
AUTO_READ_PLACEHOLDER = "Enter Second(s)"
AUTO_READ_COMMANDS = {
    "tag_id": bytes.fromhex("24110100E1F023"),
    "serial": bytes.fromhex("24110101F1D123"),
    "vin": bytes.fromhex("24110102C1B223"),
    "axle": bytes.fromhex("24110103D19323"),
    "registration": bytes.fromhex("24110104A17423"),
    "gvw": bytes.fromhex("24110105B15523"),
}

PLACEHOLDERS = {
    "tag_id": TAG_ID_PLACEHOLDER,
    "serial": SERIAL_PLACEHOLDER,
    "vin": VIN_PLACEHOLDER,
    "axle": AXLE_PLACEHOLDER,
    "gvw": GVW_PLACEHOLDER,
    "registration": REGISTRATION_PLACEHOLDER,
}

PLACEHOLDER_COLOR = "#9CA3AF"
NORMAL_COLOR = "#F9FAFB"


class TagFormFrame:
    """Component managing the Tag Data form grid, validation, and individual Read/Write buttons."""

    def __init__(self, parent_frame, root, reader, log_console_getter, reset_reader_status_cb=None, timeout_cb=None):
        self.root = root
        self.reader = reader
        self.get_log_console = log_console_getter
        self.reset_reader_status_cb = reset_reader_status_cb
        self.timeout_cb = timeout_cb

        self.reader.set_disconnect_callback(self._handle_reader_disconnect)

        self.field_vars = {}
        self.entry_widgets = {}
        self.interval_vars = {}
        self.interval_widgets = {}
        self.pending_requests = {}  # Maps param_id -> dict of command metadata
        self.request_counter = 0
        self.auto_read_intervals = {}
        self.auto_read_jobs = {}
        self.auto_read_active = {}

        self.form_container = tk.LabelFrame(
            parent_frame,
            text="Tag Data Fields",
            padx=16,
            pady=8,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 12, "bold"),
        )
        self.form_container.pack(side="left", fill="both", expand=False, padx=(0, 10), pady=(0, 8))
        self.form_container.configure(width=760)
        self.form_container.pack_propagate(False)

        self.form_grid = ttkb.Frame(self.form_container)
        self.form_grid.pack(anchor="nw", padx=5, pady=(17, 5))
        self.form_grid.columnconfigure(0, minsize=170)
        self.form_grid.columnconfigure(1, minsize=72)
        self.form_grid.columnconfigure(2, minsize=82)
        self.form_grid.columnconfigure(3, minsize=150)
        self.form_grid.columnconfigure(4, minsize=180)

        self._build_fields()
        self._build_action_buttons()
        self._build_response_section()

    def _build_response_section(self):
        self.response_frame = tk.LabelFrame(
            self.form_container,
            text="Response",
            padx=12,
            pady=10,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        )
        self.response_frame.pack(fill="x", padx=5, pady=(10, 5))

        response_row = ttkb.Frame(self.response_frame)
        response_row.pack(fill="x")

        self.response_status_label = ttkb.Label(
            response_row,
            text="No response",
            foreground="#9CA3AF",
            style="Field.TLabel",
        )
        self.response_status_label.pack(side="left", padx=(0, 8))

        self.response_value_label = ttkb.Label(
            response_row,
            text="Waiting for reader response.",
            foreground="#E2E8F0",
            style="Field.TLabel",
            anchor="w",
        )
        self.response_value_label.pack(side="left", fill="x", expand=True)

        self.copy_response_button = ttkb.Button(
            response_row,
            text="Copy",
            command=self.copy_response,
            bootstyle="secondary",
            width=8,
        )
        self.copy_response_button.pack(side="right", padx=(8, 0))

        self._response_text = ""

    def show_response(self, response_text: str, success: bool = True):
        self._response_text = response_text
        self.response_status_label.configure(
            text="success" if success else "Error",
            foreground="#10B981" if success else "#EF4444",
        )
        self.response_value_label.configure(text=response_text or "No response data.")

    def copy_response(self):
        if not self._response_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self._response_text)
        self.root.update()

    def _build_fields(self):
        visible_row_index = 0
        for label_text, var_name in FIELD_ROWS:
            if var_name in HIDDEN_FIELD_NAMES:
                continue

            ttkb.Label(self.form_grid, text=label_text, style="Field.TLabel").grid(
                row=visible_row_index * 2, column=0, columnspan=5, sticky="w", pady=(0, 2)
            )

            var = tk.StringVar()
            self.field_vars[var_name] = var
            entry_options = {
                "textvariable": var,
                "width": 30,
                "bootstyle": "info",
                "state": "normal",
            }

            if var_name == "tag_id":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_tag_id_entry),
                    "%P",
                )
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "serial":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_serial_entry),
                    "%P",
                )
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "vin":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_vin_entry),
                    "%P",
                )
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "registration":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_registration_entry),
                    "%P",
                )
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "axle":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_numeric_range_entry),
                    "%P",
                    5,
                )
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "gvw":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_numeric_range_entry),
                    "%P",
                    10,
                )
                entry = ttkb.Entry(self.form_grid, **entry_options)
            else:
                entry = ttkb.Entry(self.form_grid, **entry_options)

            entry.grid(
                row=visible_row_index * 2 + 1,
                column=0,
                sticky="w",
                padx=(0, 14),
                pady=(0, 8),
            )
            self.entry_widgets[var_name] = entry

            if var_name in PLACEHOLDERS:
                ph = PLACEHOLDERS[var_name]
                var.set(ph)
                entry.configure(foreground=PLACEHOLDER_COLOR)
                entry.bind("<FocusIn>", lambda e, name=var_name: self._clear_placeholder(e, name))
                entry.bind("<FocusOut>", lambda e, name=var_name: self._restore_placeholder(e, name))

            # Read button alongside field
            ttkb.Button(
                self.form_grid,
                text="Read",
                command=lambda name=var_name: self.read_field(name),
                bootstyle="info",
                width=7,
            ).grid(
                row=visible_row_index * 2 + 1,
                column=1,
                sticky="w",
                padx=(14, 12),
                pady=(0, 8),
            )

            if var_name == "tag_id":
                self._build_auto_read_interval_entry(var_name, visible_row_index, column=2)
            elif var_name in AUTO_READ_FIELDS:
                ttkb.Button(
                    self.form_grid,
                    text="Write",
                    command=lambda name=var_name: self.write_field(name),
                    bootstyle="success",
                    width=7,
                ).grid(
                    row=visible_row_index * 2 + 1,
                    column=2,
                    sticky="w",
                    padx=(23, 0),
                    pady=(0, 8),
                )
                self._build_auto_read_interval_entry(var_name, visible_row_index, column=3)
            else:
                ttkb.Button(
                    self.form_grid,
                    text="Write",
                    command=lambda name=var_name: self.write_field(name),
                    bootstyle="success",
                    width=7,
                ).grid(
                    row=visible_row_index * 2 + 1,
                    column=2,
                    sticky="w",
                    padx=(2, 0),
                    pady=(0, 8),
                )

            visible_row_index += 1

    def _build_auto_read_interval_entry(self, field_name: str, row_index: int, column: int):
        var = tk.StringVar(value=AUTO_READ_PLACEHOLDER)
        self.interval_vars[field_name] = var
        entry_options = {
            "textvariable": var,
            "width": 14,
            "bootstyle": "info",
            "state": "normal",
        }
        entry_options["validate"] = "key"
        entry_options["validatecommand"] = (
            self.root.register(self._validate_auto_read_interval_input),
            "%P",
        )
        entry = ttkb.Entry(self.form_grid, **entry_options)
        entry.grid(row=row_index * 2 + 1, column=column, sticky="w", padx=(8, 0), pady=(0, 8))
        self.interval_widgets[field_name] = entry
        entry.configure(foreground=PLACEHOLDER_COLOR)
        entry.bind("<FocusIn>", lambda e, name=field_name: self._clear_auto_read_placeholder(e, name))
        entry.bind("<FocusOut>", lambda e, name=field_name: self._restore_auto_read_placeholder(e, name))
        entry.bind("<Return>", lambda e, name=field_name: self._on_auto_read_interval_enter(e, name))
        entry.bind("<KP_Enter>", lambda e, name=field_name: self._on_auto_read_interval_enter(e, name))

    def _validate_auto_read_interval_input(self, new_value: str) -> bool:
        if new_value == "":
            return True
        return new_value.isdigit()

    def _clear_auto_read_placeholder(self, event, field_name: str):
        if self.interval_vars[field_name].get() == AUTO_READ_PLACEHOLDER:
            self.interval_vars[field_name].set("")
            event.widget.configure(foreground=NORMAL_COLOR)

    def _restore_auto_read_placeholder(self, event, field_name: str):
        if self.interval_vars[field_name].get().strip() == "":
            self.interval_vars[field_name].set(AUTO_READ_PLACEHOLDER)
            event.widget.configure(foreground=PLACEHOLDER_COLOR)

    def _handle_reader_disconnect(self):
        self._stop_all_auto_reads()

    def _build_action_buttons(self):
        # These global form actions are intentionally hidden per product requirement.
        pass

    def _clear_placeholder(self, event, var_name: str):
        ph = PLACEHOLDERS.get(var_name, "")
        if self.field_vars[var_name].get() == ph:
            self.field_vars[var_name].set("")
            event.widget.configure(foreground=NORMAL_COLOR)

    def _restore_placeholder(self, event, var_name: str):
        ph = PLACEHOLDERS.get(var_name, "")
        if self.field_vars[var_name].get().strip() == "":
            self.field_vars[var_name].set(ph)
            event.widget.configure(foreground=PLACEHOLDER_COLOR)

    def get_field_value(self, field_name: str) -> str:
        val = self.field_vars[field_name].get().strip()
        if field_name in PLACEHOLDERS and val == PLACEHOLDERS[field_name]:
            return ""
        return val

    def set_field_value(self, field_name: str, value: str):
        if field_name in self.field_vars:
            self.field_vars[field_name].set(value)
            widget = self.entry_widgets.get(field_name)
            if widget:
                widget.configure(foreground=NORMAL_COLOR)

    def clear_field_value(self, field_name: str):
        if field_name in self.field_vars:
            self.field_vars[field_name].set("")
            widget = self.entry_widgets.get(field_name)
            if widget:
                widget.configure(foreground=NORMAL_COLOR)

    def _register_pending_request(self, param_id: int, field_label: str, operation: str, cmd_hex: str, conv_type: str, field_name: str):
        self.request_counter += 1
        req_id = self.request_counter
        self.pending_requests[param_id] = {
            "req_id": req_id,
            "Name": field_label,
            "Operation": operation,
            "Command Sent": cmd_hex,
            "Conversion": conv_type,
            "var_name": field_name,
        }
        # Schedule 5-second (5000ms) timeout
        self.root.after(5000, lambda p_id=param_id, r_id=req_id, name=field_label, op=operation: self._handle_request_timeout(p_id, r_id, name, op))

    def _handle_request_timeout(self, param_id: int, req_id: int, field_label: str, operation: str):
        if param_id in self.pending_requests and self.pending_requests[param_id].get("req_id") == req_id:
            req_info = self.pending_requests.pop(param_id)
            log_console = self.get_log_console()
            write_log(f"UART RX Timeout: No reply from reader within 5 seconds for {field_label}", log_console)
            
            log_console.append_json(
                name=field_label,
                operation=operation,
                command_sent=req_info.get("Command Sent", ""),
                response_received="TIMEOUT",
                conversion=req_info.get("Conversion", ""),
                medium="UART",
            )
            
            if callable(self.timeout_cb):
                self.timeout_cb(field_label)

    def _transmit_auto_read_command(self, parameter: str):
        log_console = self.get_log_console()
        cmd_hex, conv_type, field_label, param_id = READ_COMMANDS[parameter]
        cmd_bytes = AUTO_READ_COMMANDS[parameter]

        if not self.reader.is_connected():
            self._stop_auto_read(parameter)
            write_log("Auto Read stopped because reader disconnected.", log_console)
            return

        self._register_pending_request(param_id, field_label, "Read", cmd_hex, conv_type, parameter)
        self.reader.write_bytes(cmd_bytes)
        write_log("AUTO READ", log_console)
        write_log(f"Parameter : {field_label}", log_console)
        write_log(f"Interval : {self.auto_read_intervals.get(parameter, 0)} seconds", log_console)
        write_log(f"UART TX (hex): {cmd_hex}", log_console)

    def _run_auto_read(self, parameter: str):
        self.auto_read_jobs.pop(parameter, None)
        if not self.auto_read_active.get(parameter):
            return

        if not self.reader.is_connected():
            self._stop_auto_read(parameter)
            write_log("Auto Read stopped because reader disconnected.", self.get_log_console())
            return

        self._transmit_auto_read_command(parameter)
        interval_seconds = self.auto_read_intervals.get(parameter)
        if interval_seconds is None:
            self._stop_auto_read(parameter)
            return
        self.auto_read_jobs[parameter] = self.root.after(interval_seconds * 1000, lambda p=parameter: self._run_auto_read(p))

    def start_auto_read(self, parameter: str):
        if parameter not in AUTO_READ_COMMANDS:
            return
        interval_seconds = self.auto_read_intervals.get(parameter)
        if interval_seconds is None:
            return
        self._stop_auto_read(parameter)
        self.auto_read_active[parameter] = True
        self.auto_read_jobs[parameter] = self.root.after(interval_seconds * 1000, lambda p=parameter: self._run_auto_read(p))

    def stop_auto_read(self, parameter: str):
        self._stop_auto_read(parameter)

    def restart_auto_read(self, parameter: str):
        self.start_auto_read(parameter)

    def _stop_auto_read(self, parameter: str):
        self.auto_read_active[parameter] = False
        job = self.auto_read_jobs.pop(parameter, None)
        if job is not None:
            self.root.after_cancel(job)

    def _stop_all_auto_reads(self):
        for parameter in list(AUTO_READ_COMMANDS.keys()):
            self._stop_auto_read(parameter)
        write_log("Auto Read stopped because reader disconnected.", self.get_log_console())

    def _on_auto_read_interval_enter(self, event, parameter: str):
        raw_value = self.interval_vars.get(parameter, tk.StringVar()).get().strip()
        if raw_value in ("", AUTO_READ_PLACEHOLDER):
            # An empty interval is optional: Enter performs one normal read.
            self.read_field(parameter)
            return
        self._configure_auto_read_interval(parameter, send_immediately=False)

    def _configure_auto_read_interval(self, parameter: str, send_immediately: bool):
        raw_value = self.interval_vars.get(parameter, tk.StringVar()).get().strip()
        if raw_value == "":
            self.stop_auto_read(parameter)
            return

        if not self._validate_auto_read_interval(raw_value):
            self.stop_auto_read(parameter)
            messagebox.showwarning("Auto Read Interval", "Please enter a value between 1 and 86400 seconds.")
            return

        interval_seconds = int(raw_value)
        self.auto_read_intervals[parameter] = interval_seconds
        self._stop_auto_read(parameter)
        self.auto_read_active[parameter] = True
        if send_immediately:
            self._transmit_auto_read_command(parameter)
        self.auto_read_jobs[parameter] = self.root.after(
            interval_seconds * 1000,
            lambda p=parameter: self._run_auto_read(p),
        )

    def _validate_auto_read_interval(self, value: str) -> bool:
        if value == "":
            return False
        if not value.isdigit():
            return False
        numeric = int(value)
        return 1 <= numeric <= 86400

    def read_field(self, field_name: str):
        log_console = self.get_log_console()

        if field_name in READ_COMMANDS:
            if field_name == "tag_id" and field_name in self.interval_vars:
                raw_interval = self.interval_vars[field_name].get().strip()
                if raw_interval not in ("", AUTO_READ_PLACEHOLDER):
                    self._configure_auto_read_interval(field_name, send_immediately=True)
                    return

            cmd_hex, conv_type, field_label, param_id = READ_COMMANDS[field_name]
            cmd_bytes = bytes.fromhex(cmd_hex)
            if self.reader.is_connected():
                self._register_pending_request(param_id, field_label, "Read", cmd_hex, conv_type, field_name)
                self.reader.write_bytes(cmd_bytes)
                write_log(f"UART TX Read Command ({field_label}): {cmd_hex}", log_console)
            else:
                write_log(f"Read command failed for {field_name}: reader not connected", log_console)
                messagebox.showwarning("Read Field", "Connect the reader before reading.")
        else:
            value = self.get_field_value(field_name)
            if value:
                write_log(f"Read field '{field_name}' : {value}", log_console)
                messagebox.showinfo("Read Field", f"{field_name.replace('_', ' ').title()} loaded.")
            else:
                write_log(f"Read field '{field_name}' is empty", log_console)
                messagebox.showwarning("Read Field", "This field is empty.")

    def read_all_fields(self):
        """Sequentially transmit Read commands for all fields spaced 1000ms apart."""
        log_console = self.get_log_console()

        if not self.reader.is_connected():
            write_log("Read All failed: reader not connected", log_console)
            messagebox.showwarning("Read All", "Connect the reader before reading fields.")
            return

        write_log("Starting Read All fields sequence (1000ms delay)...", log_console)
        commands = list(READ_COMMANDS.items())
        interval_ms = 1000  # 1000ms delay between commands

        def _send_next(index=0):
            if index >= len(commands):
                write_log("Read All sequence completed dispatching.", log_console)
                return

            field_name, (cmd_hex, conv_type, field_label, param_id) = commands[index]
            if self.reader.is_connected():
                cmd_bytes = bytes.fromhex(cmd_hex)
                self._register_pending_request(param_id, field_label, "Read", cmd_hex, conv_type, field_name)
                self.reader.write_bytes(cmd_bytes)
                write_log(f"UART TX Read Command ({field_label}): {cmd_hex}", log_console)

            # Schedule next field request after 1000ms
            self.root.after(interval_ms, lambda: _send_next(index + 1))

        _send_next(0)

    def write_field(self, field_name: str):
        log_console = self.get_log_console()
        val = self.get_field_value(field_name)

        if not val:
            write_log(f"Write {field_name} failed: field is empty", log_console)
            messagebox.showwarning("Write Field", f"Please enter a value for {field_name.replace('_', ' ').title()} before writing.")
            return

        try:
            # Build 0x29 SET Transmission Frame with CRC-16/CCITT-FALSE
            frame_bytes, frame_hex, metadata = build_write_transmission_frame(field_name, val)
            
            if self.reader.is_connected():
                param_id = int(metadata["Field_ID"], 16) if "Field_ID" in metadata else 0
                self._register_pending_request(param_id, metadata["Name"], "Write", frame_hex, metadata["Conversion"], field_name)
                self.reader.write_bytes(frame_bytes)
                write_log(f"UART TX Write Transmission Frame ({metadata['Name']}): {frame_hex}", log_console)
            else:
                write_log(f"Write command failed for {field_name}: reader not connected", log_console)
                messagebox.showwarning("Write Field", "Connect the reader before writing.")
        except Exception as e:
            write_log(f"Write field error: {e}", log_console)
            messagebox.showerror("Write Field Error", str(e))

    def clear_fields(self):
        self._stop_all_auto_reads()

        for name, var in self.field_vars.items():
            var.set("")
            if name in PLACEHOLDERS:
                ph = PLACEHOLDERS[name]
                var.set(ph)
                widget = self.entry_widgets.get(name)
                if widget:
                    widget.configure(foreground=PLACEHOLDER_COLOR)

        if callable(self.reset_reader_status_cb):
            self.reset_reader_status_cb()

        write_log("Form cleared", self.get_log_console())
