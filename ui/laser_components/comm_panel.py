"""Serial communication control panel."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from communication.serial_reader import list_available_ports


class CommPanel(ttk.LabelFrame):
    """Control panel for serial port selection and connection state."""

    def __init__(
        self,
        parent,
        default_port: str = "COM3",
        default_baud: int = 115200,
        on_connect: Optional[Callable[[str, int], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, text="RFID Reader Serial Connection", padding=(10, 8))
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.is_connected = False

        # Grid config
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)

        # Port selection
        ttk.Label(self, text="Port:").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.port_var = tk.StringVar(value=default_port)
        self.port_combo = ttk.Combobox(self, textvariable=self.port_var, width=12)
        self.port_combo.grid(row=0, column=1, sticky="ew", padx=(0, 6))

        # Refresh ports button
        self.refresh_btn = ttk.Button(self, text="⟳", width=3, command=self.refresh_ports)
        self.refresh_btn.grid(row=0, column=2, padx=(0, 8))

        # Baudrate selection
        ttk.Label(self, text="Baud:").grid(row=0, column=3, sticky="w", padx=(0, 4))
        self.baud_var = tk.IntVar(value=default_baud)
        self.baud_combo = ttk.Combobox(
            self,
            textvariable=self.baud_var,
            values=[9600, 19200, 38400, 57600, 115200, 230400],
            width=10,
            state="readonly",
        )
        self.baud_combo.grid(row=0, column=4, sticky="ew", padx=(0, 10))

        # Connect / Disconnect button
        self.toggle_btn = tk.Button(
            self,
            text="Connect",
            bg="#2563EB",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=12,
            pady=2,
            command=self._handle_toggle,
        )
        self.toggle_btn.grid(row=0, column=5, padx=(0, 8))

        # Status badge
        self.status_badge = tk.Label(
            self,
            text="DISCONNECTED",
            font=("Segoe UI", 8, "bold"),
            bg="#FEE2E2",
            fg="#991B1B",
            padx=8,
            pady=3,
            relief="groove",
        )
        self.status_badge.grid(row=0, column=6)

        self.refresh_ports()

    def refresh_ports(self):
        """Scan available serial ports."""
        ports = list_available_ports()
        self.port_combo["values"] = ports
        current = self.port_var.get()
        if ports and (not current or current not in ports):
            self.port_var.set(ports[0])

    def _handle_toggle(self):
        if self.is_connected:
            if self.on_disconnect:
                self.on_disconnect()
        else:
            port = self.port_var.get().strip()
            baud = self.baud_var.get()
            if self.on_connect:
                self.on_connect(port, baud)

    def set_connected_state(self, connected: bool):
        self.is_connected = connected
        if connected:
            self.toggle_btn.config(text="Disconnect", bg="#DC2626")
            self.status_badge.config(text="CONNECTED", bg="#DCFCE7", fg="#166534")
            self.port_combo.config(state="disabled")
            self.baud_combo.config(state="disabled")
            self.refresh_btn.config(state="disabled")
        else:
            self.toggle_btn.config(text="Connect", bg="#2563EB")
            self.status_badge.config(text="DISCONNECTED", bg="#FEE2E2", fg="#991B1B")
            self.port_combo.config(state="normal")
            self.baud_combo.config(state="readonly")
            self.refresh_btn.config(state="normal")
