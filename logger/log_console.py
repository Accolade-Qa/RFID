import csv
import json
import os
import threading
from datetime import datetime
from tkinter import scrolledtext

from config import CSV_DEFAULT_PATH, JSON_DEFAULT_PATH, LOG_DEFAULT_PATH

MAX_LOG_LINES = 1000
JSON_LOG_FILE = JSON_DEFAULT_PATH


class LogConsole(scrolledtext.ScrolledText):
    """Custom ScrolledText widget for activity logging and JSON file persistence."""

    def __init__(self, master=None, max_lines: int = MAX_LOG_LINES, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            width=60,
            height=14,
            state="disabled",
            font=("Consolas", 10),
            wrap="word",
            bg="#111827",
            fg="#F9FAFB",
            insertbackground="#F9FAFB",
        )
        self.file_path = LOG_DEFAULT_PATH
        self.auto_save = True
        self.max_lines = max_lines
        self.line_count = 0
        self.json_file_path = JSON_LOG_FILE
        self.csv_file_path = CSV_DEFAULT_PATH
        self._lock = threading.Lock()

    def append(self, message: str):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{current_time}] {message}\n"

        self.configure(state="normal")
        self.insert("end", line)
        self.line_count += 1

        if self.line_count > self.max_lines:
            overflow = self.line_count - self.max_lines
            self.delete("1.0", f"{overflow + 1}.0")
            self.line_count = self.max_lines

        self.see("end")
        self.configure(state="disabled")

        if self.auto_save and self.file_path:
            try:
                with self._lock:
                    with open(self.file_path, "a", encoding="utf-8") as f:
                        f.write(line)
            except Exception:
                pass

    def append_json(self, name: str, operation: str, command_sent: str,
                    response_received: str = "", conversion: str = "",
                    medium: str = "UART") -> dict:
        """Record structured JSON entry directly to activity_records.json without printing raw JSON in console."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        record = {
            "Name": name,
            "Operation": operation,
            "Command Sent": command_sent,
            "Response Received": response_received,
            "Medium of transmission": medium,
            "Time Stamp": current_time,
        }

        # Save to activity_records.json
        try:
            with self._lock:
                records = []
                if os.path.exists(self.json_file_path):
                    try:
                        with open(self.json_file_path, "r", encoding="utf-8") as jf:
                            records = json.load(jf)
                            if not isinstance(records, list):
                                records = []
                    except Exception:
                        records = []

                records.append(record)
                with open(self.json_file_path, "w", encoding="utf-8") as jf:
                    json.dump(records, jf, indent=2)
        except Exception:
            pass

        return record

    def set_file_path(self, path: str):
        self.file_path = path

    def append_csv(self, name: str, operation: str, command_sent: str,
                   response_received: str = "", conversion: str = "",
                   medium: str = "UART") -> bool:
        """Append one structured response record to the application CSV log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fieldnames = [
            "Name",
            "Operation",
            "Command Sent",
            "Response Received",
            "Medium of transmission",
            "Date and Time",
        ]
        record = {
            "Name": name,
            "Operation": operation,
            "Command Sent": command_sent,
            "Response Received": response_received,
            "Medium of transmission": medium,
            "Date and Time": timestamp,
        }

        try:
            with self._lock:
                existing_rows = []
                has_existing_header = False
                rewrite_file = False
                if os.path.exists(self.csv_file_path) and os.path.getsize(self.csv_file_path) > 0:
                    with open(self.csv_file_path, "r", newline="", encoding="utf-8") as csv_file:
                        reader = csv.DictReader(csv_file)
                        has_existing_header = reader.fieldnames is not None
                        existing_rows = [
                            {field: row.get(field, "") for field in fieldnames}
                            for row in reader
                        ]
                        rewrite_file = reader.fieldnames != fieldnames

                file_mode = "w" if rewrite_file else "a"
                with open(self.csv_file_path, file_mode, newline="", encoding="utf-8") as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    if rewrite_file or not has_existing_header:
                        writer.writeheader()
                        writer.writerows(existing_rows)
                    writer.writerow(record)
            return True
        except Exception:
            return False

    def enable_auto_save(self, enable: bool):
        self.auto_save = bool(enable)

    def save_all(self, path: str = None) -> bool:
        p = path or self.file_path
        if not p:
            return False
        try:
            text = self.get("1.0", "end")
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception:
            return False

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.line_count = 0
        self.configure(state="disabled")


def write_log(message: str, log_box: LogConsole = None):
    if log_box is not None:
        log_box.append(message)
