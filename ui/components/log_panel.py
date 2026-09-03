import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttkb
from config import LOG_DEFAULT_PATH
from logger import LogConsole, write_log


class LogPanelFrame:
    """Component managing the LogConsole widget and controls (auto-save, path, clear)."""

    def __init__(self, parent_frame, root):
        self.root = root

        self.log_frame = tk.LabelFrame(
            parent_frame,
            text="Activity Log",
            padx=10,
            pady=10,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        )
        self.log_frame.pack(fill="both", expand=True, pady=(0, 8))
        self.log_frame.pack_propagate(False)
        self.log_frame.pack_forget()

        self.auto_save_var = tk.BooleanVar(value=True)
        self.log_path_var = tk.StringVar(value=LOG_DEFAULT_PATH)

        self._build_widgets()

    def _build_widgets(self):
        controls_subframe = ttkb.Frame(self.log_frame)
        controls_subframe.pack(fill="x", pady=(0, 8))

        auto_save_cb = ttkb.Checkbutton(
            controls_subframe,
            text="Auto Save Logs",
            variable=self.auto_save_var,
            command=self.toggle_auto_save,
            bootstyle="info",
        )
        auto_save_cb.pack(side="left", padx=(0, 8))

        log_path_entry = ttkb.Entry(
            controls_subframe,
            textvariable=self.log_path_var,
            width=70,
            bootstyle="info",
        )
        log_path_entry.pack(side="left", expand=True, padx=(0, 8))

        browse_btn = ttkb.Button(
            controls_subframe,
            text="Browse",
            command=self.browse_log_path,
            bootstyle="secondary",
        )
        browse_btn.pack(side="left")

        clear_log_btn = ttkb.Button(
            controls_subframe,
            text="Clear Log",
            command=self.clear_log,
            bootstyle="secondary",
        )
        clear_log_btn.pack(side="left", padx=(8, 0))

        self.log_console = LogConsole(self.log_frame)
        self.log_console.set_file_path(self.log_path_var.get())
        self.log_console.pack(fill="both", expand=True)

        write_log("RFID Communicator started", self.log_console)
        self.log_console.enable_auto_save(True)

    def browse_log_path(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Select log file",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("All files", "*")],
        )
        if path:
            self.log_path_var.set(path)
            self.log_console.set_file_path(path)

    def toggle_auto_save(self):
        enabled = bool(self.auto_save_var.get())
        self.log_console.enable_auto_save(enabled)
        write_log(f"Auto-save {'enabled' if enabled else 'disabled'}", self.log_console)

    def clear_log(self):
        self.log_console.clear()
