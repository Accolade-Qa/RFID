"""RFID reading and Tag input component."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class RFIDPanel(ttk.LabelFrame):
    """Panel managing Tag ID input, RFID read triggers, and Auto-read."""

    def __init__(
        self,
        parent,
        on_read_tag: Optional[Callable[[], None]] = None,
        on_auto_read_toggle: Optional[Callable[[bool, float], None]] = None,
        on_tag_changed: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent, text="RFID Tag Input & Reader Control", padding=(12, 10))
        self.on_read_tag = on_read_tag
        self.on_auto_read_toggle = on_auto_read_toggle
        self.on_tag_changed = on_tag_changed

        self.columnconfigure(1, weight=1)

        # Row 0: Tag ID Input Box
        lbl_tag = ttk.Label(self, text="Tag ID:", font=("Segoe UI", 10, "bold"))
        lbl_tag.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)

        self.tag_var = tk.StringVar(value="")
        self.tag_var.trace_add("write", self._on_var_changed)

        self.tag_entry = ttk.Entry(
            self,
            textvariable=self.tag_var,
            font=("Consolas", 12, "bold"),
        )
        self.tag_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=4)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=0, column=2, sticky="e", pady=4)

        self.read_btn = tk.Button(
            btn_frame,
            text="📡 Read Tag",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=10,
            pady=3,
            command=self._handle_read,
        )
        self.read_btn.pack(side="left", padx=(0, 4))

        self.clear_btn = ttk.Button(
            btn_frame,
            text="Clear",
            command=self.clear_tag,
            width=6,
        )
        self.clear_btn.pack(side="left")

        # Row 1: Auto-Read and Status Info
        row1_frame = ttk.Frame(self)
        row1_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        row1_frame.columnconfigure(2, weight=1)

        self.auto_read_var = tk.BooleanVar(value=False)
        self.auto_read_chk = ttk.Checkbutton(
            row1_frame,
            text="Auto-Read Tag",
            variable=self.auto_read_var,
            command=self._handle_auto_read_toggle,
        )
        self.auto_read_chk.grid(row=0, column=0, sticky="w", padx=(0, 8))

        ttk.Label(row1_frame, text="Interval (s):").grid(row=0, column=1, sticky="w", padx=(0, 4))
        self.interval_var = tk.DoubleVar(value=2.0)
        self.interval_entry = ttk.Entry(row1_frame, textvariable=self.interval_var, width=5)
        self.interval_entry.grid(row=0, column=2, sticky="w", padx=(0, 12))

        self.status_lbl = ttk.Label(
            row1_frame,
            text="Ready to scan",
            font=("Segoe UI", 9, "italic"),
            foreground="#6B7280",
        )
        self.status_lbl.grid(row=0, column=3, sticky="e")

    def _on_var_changed(self, *args):
        val = self.tag_var.get().strip()
        if self.on_tag_changed:
            self.on_tag_changed(val)

    def _handle_read(self):
        self.status_lbl.config(text="Sending read command...", foreground="#D97706")
        if self.on_read_tag:
            self.on_read_tag()

    def _handle_auto_read_toggle(self):
        active = self.auto_read_var.get()
        try:
            interval = float(self.interval_var.get())
            if interval < 0.5:
                interval = 0.5
        except ValueError:
            interval = 2.0
            self.interval_var.set(2.0)

        if active:
            self.interval_entry.config(state="disabled")
        else:
            self.interval_entry.config(state="normal")

        if self.on_auto_read_toggle:
            self.on_auto_read_toggle(active, interval)

    def set_tag_value(self, tag_val: str):
        self.tag_var.set(tag_val)
        self.status_lbl.config(text=f"Tag updated: {len(tag_val)} chars", foreground="#059669")

    def get_tag_value(self) -> str:
        return self.tag_var.get().strip()

    def clear_tag(self):
        self.tag_var.set("")
        self.status_lbl.config(text="Tag cleared", foreground="#6B7280")

    def set_reading_state(self, is_reading: bool, msg: str = ""):
        if is_reading:
            self.read_btn.config(state="disabled", text="Reading...")
            if msg:
                self.status_lbl.config(text=msg, foreground="#D97706")
        else:
            self.read_btn.config(state="normal", text="📡 Read Tag")
            if msg:
                self.status_lbl.config(text=msg, foreground="#059669")
