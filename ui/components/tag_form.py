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
    validate_serial_entry,
    validate_vin_entry,
    validate_registration_entry,
    validate_numeric_range_entry,
    validate_gvw_decimal_entry
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

        self.field_vars = {}
        self.entry_widgets = {}
        self.pending_requests = {}  # Maps param_id -> dict of command metadata
        self.request_counter = 0

        self.form_container = tk.LabelFrame(
            parent_frame,
            text="Tag Data Fields",
            padx=20,
            pady=20,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 12, "bold"),
        )
        self.form_container.pack(side="left", fill="y", padx=(0, 10), pady=(0, 8))
        self.form_container.configure(width=650)
        self.form_container.pack_propagate(False)

        self.form_grid = ttkb.Frame(self.form_container)
        self.form_grid.pack(anchor="nw", padx=5, pady=5)

        self._build_fields()
        self._build_action_buttons()

    def _build_fields(self):
        for row_index, (label_text, var_name) in enumerate(FIELD_ROWS):
            ttkb.Label(self.form_grid, text=label_text, style="Field.TLabel").grid(
                row=row_index * 2, column=0, columnspan=3, sticky="w", pady=(0, 2)
            )

            var = tk.StringVar()
            self.field_vars[var_name] = var
            entry_options = {
                "textvariable": var,
                "width": 34,
                "bootstyle": "info",
                "state": "normal",
            }

            if var_name == "tag_id":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_tag_id_entry),
                    "%P",
                )
                # pyrefly: ignore [unexpected-keyword]
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "serial":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_serial_entry),
                    "%P",
                )
                # pyrefly: ignore [unexpected-keyword]
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "vin":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_vin_entry),
                    "%P",
                )
                # pyrefly: ignore [unexpected-keyword]
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "registration":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_registration_entry),
                    "%P",
                )
                # pyrefly: ignore [unexpected-keyword]
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "axle":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_numeric_range_entry),
                    "%P",
                    5,
                )
                # pyrefly: ignore [unexpected-keyword]
                entry = ttkb.Entry(self.form_grid, **entry_options)
            elif var_name == "gvw":
                entry_options["validate"] = "key"
                entry_options["validatecommand"] = (
                    self.root.register(validate_gvw_decimal_entry),
                    "%P",
                )
                # pyrefly: ignore [unexpected-keyword]
                entry = ttkb.Entry(self.form_grid, **entry_options)
            else:
                # pyrefly: ignore [unexpected-keyword]
                entry = ttkb.Entry(self.form_grid, **entry_options)

            entry.grid(row=row_index * 2 + 1, column=0, sticky="w", pady=(0, 8))
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
                # pyrefly: ignore [unexpected-keyword]
                bootstyle="info",
                width=7,
            ).grid(
                row=row_index * 2 + 1,
                column=1,
                sticky="w",
                padx=(6, 2),
                pady=(0, 8),
            )

            # Write button alongside field (except for Tag ID)
            if var_name != "tag_id":
                ttkb.Button(
                    self.form_grid,
                    text="Write",
                    command=lambda name=var_name: self.write_field(name),
                    # pyrefly: ignore [unexpected-keyword]
                    bootstyle="success",
                    width=7,
                ).grid(
                    row=row_index * 2 + 1,
                    column=2,
                    sticky="w",
                    padx=(2, 0),
                    pady=(0, 8),
                )

    def _build_action_buttons(self):
        button_frame = ttkb.Frame(self.form_container)
        button_frame.pack(fill="x", pady=(5, 0))

        button_center = ttkb.Frame(button_frame)
        button_center.pack(anchor="center")

        ttkb.Button(
            button_center,
            text="Read All",
            command=self.read_all_fields,
            # pyrefly: ignore [unexpected-keyword]
            bootstyle="info",
            width=16,
        ).pack(side="left", padx=(0, 12))

        ttkb.Button(
            button_center,
            text="Clear Form",
            command=self.clear_fields,
            # pyrefly: ignore [unexpected-keyword]
            bootstyle="warning",
            width=16,
        ).pack(side="left")

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

    def _get_medium_name(self) -> str:
        if hasattr(self.reader, "bustype") or "CAN" in self.reader.__class__.__name__.upper():
            return "CAN"
        return "UART"

    def _handle_request_timeout(self, param_id: int, req_id: int, field_label: str, operation: str):
        if param_id in self.pending_requests and self.pending_requests[param_id].get("req_id") == req_id:
            req_info = self.pending_requests.pop(param_id)
            log_console = self.get_log_console()
            medium_name = self._get_medium_name()
            write_log(f"{medium_name} RX Timeout: No reply from reader within 5 seconds for {field_label}", log_console)
            
            log_console.append_json(
                name=field_label,
                operation=operation,
                command_sent=req_info.get("Command Sent", ""),
                response_received="TIMEOUT",
                conversion=req_info.get("Conversion", ""),
                medium=medium_name,
            )
            
            if callable(self.timeout_cb):
                self.timeout_cb(field_label)

    def read_field(self, field_name: str):
        log_console = self.get_log_console()
        medium_name = self._get_medium_name()

        if field_name in READ_COMMANDS:
            cmd_hex, conv_type, field_label, param_id = READ_COMMANDS[field_name]
            cmd_bytes = bytes.fromhex(cmd_hex)
            if self.reader.is_connected():
                self._register_pending_request(param_id, field_label, "Read", cmd_hex, conv_type, field_name)
                self.reader.write_bytes(cmd_bytes)
                write_log(f"{medium_name} TX Read Command ({field_label}): {cmd_hex}", log_console)
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
        """Sequentially transmit Read commands for all fields spaced 600ms apart."""
        log_console = self.get_log_console()
        medium_name = self._get_medium_name()

        if not self.reader.is_connected():
            write_log("Read All failed: reader not connected", log_console)
            messagebox.showwarning("Read All", "Connect the reader before reading fields.")
            return

        self.clear_pending_requests()
        write_log("Starting Read All fields sequence...", log_console)
        commands = list(READ_COMMANDS.items())
        interval_ms = 1000

        def _send_next(index=0):
            if index >= len(commands):
                write_log("Read All sequence completed dispatching.", log_console)
                return

            field_name, (cmd_hex, conv_type, field_label, param_id) = commands[index]
            if self.reader.is_connected():
                cmd_bytes = bytes.fromhex(cmd_hex)
                self._register_pending_request(param_id, field_label, "Read", cmd_hex, conv_type, field_name)
                self.reader.write_bytes(cmd_bytes)
                write_log(f"{medium_name} TX Read Command ({field_label}): {cmd_hex}", log_console)

            self.root.after(interval_ms, lambda: _send_next(index + 1))

        _send_next(0)

    def write_field(self, field_name: str):
        log_console = self.get_log_console()
        val = self.get_field_value(field_name)
        medium_name = self._get_medium_name()

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
                write_log(f"{medium_name} TX Write Transmission Frame ({metadata['Name']}): {frame_hex}", log_console)
            else:
                write_log(f"Write command failed for {field_name}: reader not connected", log_console)
                messagebox.showwarning("Write Field", "Connect the reader before writing.")
        except Exception as e:
            write_log(f"Write field error: {e}", log_console)
            messagebox.showerror("Write Field Error", str(e))

    def clear_pending_requests(self):
        """Immediately clear pending request tracking (e.g. on disconnect or medium change)."""
        self.pending_requests.clear()

    def clear_fields(self):
        self.clear_pending_requests()
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
