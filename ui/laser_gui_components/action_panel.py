"""Laser Marking Action and Live Status Feedback Panel."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ActionPanel(ttk.LabelFrame):
    """Panel with execution buttons (Manual Mark, Auto Continuous Pipeline, Stop) and live feedback banner."""

    def __init__(
        self,
        parent,
        on_write_file: Optional[Callable[[], None]] = None,
        on_mark: Optional[Callable[[], None]] = None,
        on_auto_pipeline_toggle: Optional[Callable[[bool], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, text="Laser Marking Actions & Hardware Feedback", padding=(12, 10))
        self.on_write_file = on_write_file
        self.on_mark = on_mark
        self.on_auto_pipeline_toggle = on_auto_pipeline_toggle
        self.on_stop = on_stop

        self.is_pipeline_active = False

        self.columnconfigure(0, weight=1)

        # Row 0: Action Buttons
        btn_grid = ttk.Frame(self)
        btn_grid.grid(row=0, column=0, sticky="ew", pady=(2, 6))
        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)
        btn_grid.columnconfigure(2, weight=2)
        btn_grid.columnconfigure(3, weight=1)

        self.write_btn = tk.Button(
            btn_grid,
            text="✍ Update Text File",
            bg="#3B82F6",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=10,
            pady=5,
            command=self._handle_write,
        )
        self.write_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.mark_btn = tk.Button(
            btn_grid,
            text="⚡ Mark Tag (F2)",
            bg="#D97706",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=10,
            pady=5,
            command=self._handle_mark,
        )
        self.mark_btn.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        self.pipeline_btn = tk.Button(
            btn_grid,
            text="🚀 AUTO READ & MARK (CONTINUOUS PIPELINE)",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="raised",
            padx=12,
            pady=5,
            command=self._handle_pipeline_toggle,
        )
        self.pipeline_btn.grid(row=0, column=2, sticky="ew", padx=(0, 4))

        self.stop_btn = tk.Button(
            btn_grid,
            text="⏹ STOP (ESC)",
            bg="#DC2626",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=10,
            pady=5,
            command=self._handle_stop,
        )
        self.stop_btn.grid(row=0, column=3, sticky="ew")

        # Row 1: Live Hardware Feedback Banner
        self.feedback_banner = tk.Label(
            self,
            text="● LASER READY (WAITING FOR JOB)",
            font=("Segoe UI", 11, "bold"),
            bg="#DCFCE7",
            fg="#166534",
            padx=12,
            pady=8,
            relief="groove",
            borderwidth=2,
            anchor="center",
        )
        self.feedback_banner.grid(row=1, column=0, sticky="ew", pady=(4, 2))

    def _handle_write(self):
        if self.on_write_file:
            self.on_write_file()

    def _handle_mark(self):
        if self.on_mark:
            self.on_mark()

    def _handle_pipeline_toggle(self):
        self.is_pipeline_active = not self.is_pipeline_active
        if self.is_pipeline_active:
            self.pipeline_btn.config(
                text="⏹ STOP AUTO PIPELINE",
                bg="#DC2626",
            )
        else:
            self.pipeline_btn.config(
                text="🚀 AUTO READ & MARK (CONTINUOUS PIPELINE)",
                bg="#059669",
            )
        if self.on_auto_pipeline_toggle:
            self.on_auto_pipeline_toggle(self.is_pipeline_active)

    def _handle_stop(self):
        if self.is_pipeline_active:
            self._handle_pipeline_toggle()
        if self.on_stop:
            self.on_stop()

    def set_marking_state(self, is_marking: bool, status_msg: str = "", level: str = "INFO"):
        """Update buttons and live visual feedback banner."""
        if is_marking:
            self.mark_btn.config(state="disabled", text="Marking...")
            self.write_btn.config(state="disabled")
            self.feedback_banner.config(
                text=status_msg or "⏳ LASER MARKING IN PROGRESS (F2 ACTIVE)... WAITING FOR COMPLETION",
                bg="#FEF3C7",
                fg="#92400E",
            )
        else:
            self.mark_btn.config(state="normal", text="⚡ Mark Tag (F2)")
            self.write_btn.config(state="normal")
            if level == "SUCCESS":
                self.feedback_banner.config(
                    text=status_msg or "✅ JOB DONE (FEEDBACK: OK) — READY FOR NEXT TAG",
                    bg="#DCFCE7",
                    fg="#166534",
                )
            elif level == "WARNING":
                self.feedback_banner.config(
                    text=status_msg or "⚠️ DUPLICATE TAG DETECTED — MARKING BLOCKED",
                    bg="#FEF3C7",
                    fg="#92400E",
                )
            elif level == "ERROR":
                self.feedback_banner.config(
                    text=status_msg or "❌ MARKING FAILED",
                    bg="#FEE2E2",
                    fg="#991B1B",
                )
            else:
                self.feedback_banner.config(
                    text="● LASER READY (WAITING FOR JOB)",
                    bg="#DCFCE7",
                    fg="#166534",
                )

    def stop_pipeline(self):
        if self.is_pipeline_active:
            self.is_pipeline_active = False
            self.pipeline_btn.config(
                text="🚀 AUTO READ & MARK (CONTINUOUS PIPELINE)",
                bg="#059669",
            )
