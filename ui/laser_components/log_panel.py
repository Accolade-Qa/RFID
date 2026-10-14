"""Log and status console component."""

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText


class LogPanel(ttk.LabelFrame):
    """Real-time scrolling activity and diagnostic log console."""

    def __init__(self, parent):
        super().__init__(parent, text="Activity & Diagnostic Log", padding=(10, 8))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.text_area = ScrolledText(
            self,
            wrap=tk.WORD,
            height=12,
            font=("Consolas", 9),
            bg="#111827",
            fg="#F9FAFB",
            insertbackground="white",
        )
        self.text_area.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 6))

        # Color tags
        self.text_area.tag_config("INFO", foreground="#9CA3AF")
        self.text_area.tag_config("SUCCESS", foreground="#34D399")
        self.text_area.tag_config("WARNING", foreground="#FBBF24")
        self.text_area.tag_config("ERROR", foreground="#F87171")
        self.text_area.tag_config("HIGHLIGHT", foreground="#60A5FA", font=("Consolas", 9, "bold"))

        # Action buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.clear_btn = ttk.Button(btn_frame, text="Clear Log", command=self.clear_log, width=10)
        self.clear_btn.pack(side="left", padx=(0, 6))

        self.save_btn = ttk.Button(btn_frame, text="Save Log...", command=self.save_log, width=12)
        self.save_btn.pack(side="left")

        self.count_lbl = ttk.Label(btn_frame, text="0 events logged", font=("Segoe UI", 8), foreground="#6B7280")
        self.count_lbl.pack(side="right")

        self.log_count = 0

    def log(self, message: str, level: str = "INFO"):
        """Append a timestamped message with color styling."""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        prefix = f"[{ts}] [{level.upper()}] "
        full_line = f"{prefix}{message}\n"

        self.text_area.insert(tk.END, full_line, level.upper())
        self.text_area.see(tk.END)

        self.log_count += 1
        self.count_lbl.config(text=f"{self.log_count} events logged")

    def clear_log(self):
        self.text_area.delete("1.0", tk.END)
        self.log_count = 0
        self.count_lbl.config(text="0 events logged")

    def save_log(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log Files", "*.log"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Export Activity Log",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.text_area.get("1.0", tk.END))
                self.log(f"Log exported successfully to {file_path}", level="SUCCESS")
            except Exception as e:
                self.log(f"Failed to export log: {e}", level="ERROR")
