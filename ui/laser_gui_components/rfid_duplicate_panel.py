"""RFID Tag display, auto-read control, and Duplicate Filter monitoring panel."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional


class RfidDuplicatePanel(ttk.LabelFrame):
    """Panel managing RFID Tag reading, live duplicate verification, and lot statistics."""

    def __init__(
        self,
        parent,
        default_interval: float = 1.5,
        default_strict_duplicate: bool = True,
        on_read_tag: Optional[Callable[[], None]] = None,
        on_toggle_auto_read: Optional[Callable[[bool, float], None]] = None,
        on_view_history: Optional[Callable[[], None]] = None,
        on_clear_history: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, text="RFID Tag Input & Duplicate Protection", padding=(12, 10))
        self.on_read_tag = on_read_tag
        self.on_toggle_auto_read = on_toggle_auto_read
        self.on_view_history = on_view_history
        self.on_clear_history = on_clear_history

        self.columnconfigure(1, weight=1)

        # Row 0: Tag ID display & Manual Read Button
        ttk.Label(self, text="Scanned Tag ID:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        self.tag_var = tk.StringVar(value="")
        self.tag_entry = ttk.Entry(
            self,
            textvariable=self.tag_var,
            font=("Consolas", 12, "bold"),
        )
        self.tag_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=3)

        btn_box0 = ttk.Frame(self)
        btn_box0.grid(row=0, column=2, sticky="e", pady=3)

        self.read_btn = tk.Button(
            btn_box0,
            text="📡 Read Tag",
            bg="#2563EB",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=8,
            pady=2,
            command=self._handle_read,
        )
        self.read_btn.pack(side="left", padx=(0, 4))

        self.clear_tag_btn = ttk.Button(btn_box0, text="Clear", width=6, command=self.clear_tag)
        self.clear_tag_btn.pack(side="left")

        # Row 1: Tag Prefix & Auto-Read
        row1 = ttk.Frame(self)
        row1.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 6))

        ttk.Label(row1, text="Tag Prefix:").pack(side="left", padx=(0, 4))
        self.prefix_var = tk.StringVar(value="")
        self.prefix_entry = ttk.Entry(row1, textvariable=self.prefix_var, width=12)
        self.prefix_entry.pack(side="left", padx=(0, 16))

        self.auto_read_var = tk.BooleanVar(value=False)
        self.auto_read_chk = ttk.Checkbutton(
            row1,
            text="Auto-Read Tag (Interval:",
            variable=self.auto_read_var,
            command=self._handle_auto_toggle,
        )
        self.auto_read_chk.pack(side="left", padx=(0, 2))

        self.interval_var = tk.DoubleVar(value=default_interval)
        self.interval_entry = ttk.Entry(row1, textvariable=self.interval_var, width=4)
        self.interval_entry.pack(side="left", padx=(0, 2))
        ttk.Label(row1, text="s)").pack(side="left", padx=(0, 16))

        # Strict Duplicate Protection Checkbox
        self.strict_var = tk.BooleanVar(value=default_strict_duplicate)
        self.strict_chk = ttk.Checkbutton(
            row1,
            text="Strict Duplicate Protection (Block Already Marked Tags)",
            variable=self.strict_var,
        )
        self.strict_chk.pack(side="left")

        # Row 2: Live Duplicate Status Banner
        self.status_banner = tk.Label(
            self,
            text="● WAITING FOR RFID TAG SCAN...",
            font=("Segoe UI", 10, "bold"),
            bg="#F3F4F6",
            fg="#4B5563",
            padx=10,
            pady=6,
            relief="groove",
            borderwidth=1,
            anchor="center",
        )
        self.status_banner.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(2, 6))

        # Row 3: Statistics & History Controls
        stat_frame = ttk.Frame(self)
        stat_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(2, 2))

        self.stats_lbl = tk.Label(
            stat_frame,
            text="📊 Scanned: 0  |  Unique Marked: 0  |  Duplicates Blocked: 0",
            font=("Segoe UI", 9, "bold"),
            fg="#1F2937",
        )
        self.stats_lbl.pack(side="left")

        self.clear_hist_btn = ttk.Button(
            stat_frame,
            text="🔄 Clear History",
            width=14,
            command=self._handle_clear_history,
        )
        self.clear_hist_btn.pack(side="right", padx=(4, 0))

        self.view_hist_btn = ttk.Button(
            stat_frame,
            text="📋 View History",
            width=14,
            command=self._handle_view_history,
        )
        self.view_hist_btn.pack(side="right", padx=(4, 0))

    def _handle_read(self):
        if self.on_read_tag:
            self.on_read_tag()

    def _handle_auto_toggle(self):
        active = self.auto_read_var.get()
        interval = self.get_interval()
        if self.on_toggle_auto_read:
            self.on_toggle_auto_read(active, interval)

    def _handle_view_history(self):
        if self.on_view_history:
            self.on_view_history()

    def _handle_clear_history(self):
        if messagebox.askyesno(
            "Confirm Reset History",
            "Are you sure you want to clear marked tags history?\n\n"
            "This will archive the current list and allow previously marked tags to be marked again.",
        ):
            if self.on_clear_history:
                self.on_clear_history()

    def get_tag_value(self) -> str:
        return self.tag_var.get().strip().upper()

    def set_tag_value(self, tag: str):
        self.tag_var.set(tag.strip().upper())

    def get_prefix(self) -> str:
        return self.prefix_var.get().strip()

    def get_full_formatted_tag(self) -> str:
        tag = self.get_tag_value()
        prefix = self.get_prefix()
        return f"{prefix}{tag}" if prefix else tag

    def clear_tag(self):
        self.tag_var.set("")
        self.set_duplicate_status("WAITING")

    def get_interval(self) -> float:
        try:
            return max(float(self.interval_var.get()), 0.5)
        except ValueError:
            return 1.5

    def is_strict_duplicate_enabled(self) -> bool:
        return self.strict_var.get()

    def set_duplicate_status(self, status: str, tag_id: str = ""):
        """Update the visual duplicate status banner."""
        if status == "UNIQUE":
            self.status_banner.config(
                text=f"🟢 NEW UNIQUE TAG VERIFIED: {tag_id} — READY TO MARK",
                bg="#DCFCE7",
                fg="#166534",
            )
        elif status == "DUPLICATE":
            self.status_banner.config(
                text=f"🟡 DUPLICATE TAG DETECTED: {tag_id} — ALREADY MARKED (BLOCKED)!",
                bg="#FEF3C7",
                fg="#92400E",
            )
        elif status == "WAITING":
            self.status_banner.config(
                text="● WAITING FOR RFID TAG SCAN...",
                bg="#F3F4F6",
                fg="#4B5563",
            )
        elif status == "READING":
            self.status_banner.config(
                text="⏳ READING RFID TAG FROM ANTENNA...",
                bg="#E0E7FF",
                fg="#3730A3",
            )

    def update_statistics(self, scanned: int, marked: int, duplicates: int):
        self.stats_lbl.config(
            text=f"📊 Scanned: {scanned}  |  Unique Marked: {marked}  |  Duplicates Blocked: {duplicates}"
        )
