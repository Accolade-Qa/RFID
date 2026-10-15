"""Main Application Window for AEPL RFID Laser Marking Utility (EzCAD GUI Automation).
Integrates Serial RFID Reader -> Duplicate Prevention -> Dynamic Text File -> EzCAD F2 Hotkey Automation.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

from communication.protocol import READ_TAG_ID_CMD, parse_rfid_response_frame
from communication.uart import SerialReader
from laser.duplicate_filter import DuplicateFilter
from laser.ezcad_gui_controller import EzcadGuiController
from ui.laser_gui_components import (
    ActionPanel,
    CommPanel,
    EzcadPanel,
    HeaderComponent,
    LogPanel,
    RfidDuplicatePanel,
)


def resolve_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


APP_DIR = resolve_app_dir()
SETTINGS_FILE = APP_DIR / "laser_gui_settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "port": "COM3",
    "baudrate": 115200,
    "ezcad_exe": str(APP_DIR / "EzCad2.exe"),
    "ezd_template": str(APP_DIR / "test.ezd"),
    "input_file": str(APP_DIR / "tag_input.txt"),
    "tag_prefix": "",
    "mark_delay": 1.5,
    "strict_duplicate": True,
    "simulation_mode": False,
}


def load_gui_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.is_file():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg = dict(DEFAULT_SETTINGS)
                cfg.update(saved)
                return cfg
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_gui_settings(cfg: Dict[str, Any]):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


class RFIDLaserGuiApp:
    """Master Application Window for RFID Laser Marking via EzCAD GUI Automation."""

    def __init__(self, root: Optional[tk.Tk] = None):
        self.root = root or tk.Tk()
        self.root.title("AEPL RFID Laser Controller — EzCAD GUI Automation")
        self.root.geometry("1060x860")
        self.root.minsize(920, 720)

        self.settings = load_gui_settings()

        # Serial Reader & Buffer
        self.reader = SerialReader(
            port=self.settings.get("port", "COM3"),
            baudrate=self.settings.get("baudrate", 115200),
        )
        self.reader.set_disconnect_callback(self._on_reader_disconnected)
        self.rx_buffer = bytearray()

        # Controllers
        self.duplicate_filter = DuplicateFilter(str(APP_DIR))
        self.ezcad_controller = EzcadGuiController(
            ezcad_exe_path=self.settings.get("ezcad_exe", ""),
            input_file_path=self.settings.get("input_file", str(APP_DIR / "tag_input.txt")),
            template_path=self.settings.get("ezd_template", ""),
        )

        # State Variables
        self.is_marking: bool = False
        self.is_auto_reading: bool = False
        self.is_pipeline_active: bool = False
        self.auto_read_timer_id: Optional[str] = None
        self.pipeline_timer_id: Optional[str] = None
        self.last_scanned_tag: str = ""

        # Build UI layout
        self._build_ui()

        # Set window icon if available
        icon_path = APP_DIR / "assets" / "Acc_logo.ico"
        if icon_path.is_file():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Start Serial RX polling loop
        self.root.after(50, self._poll_serial)

        # Sync initial statistics with DuplicateFilter
        self._sync_statistics()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.main_container = ttk.Frame(self.root, padding=10)
        self.main_container.pack(fill="both", expand=True)

        sim_mode = self.settings.get("simulation_mode", False)

        # 1. Header Banner
        self.header_comp = HeaderComponent(self.main_container, is_simulation=sim_mode)
        self.header_comp.pack(fill="x", pady=(0, 6))

        # 2. Serial Port Connection Panel
        self.comm_comp = CommPanel(
            self.main_container,
            default_port=self.settings.get("port", "COM3"),
            default_baud=self.settings.get("baudrate", 115200),
            on_connect=self._connect_serial,
            on_disconnect=self._disconnect_serial,
        )
        self.comm_comp.pack(fill="x", pady=(0, 6))

        # 3. EzCAD GUI & Dynamic File Binding Panel
        self.ezcad_comp = EzcadPanel(
            self.main_container,
            default_ezcad_exe=self.settings.get("ezcad_exe", str(APP_DIR / "EzCad2.exe")),
            default_template=self.settings.get("ezd_template", str(APP_DIR / "test.ezd")),
            default_input_file=self.settings.get("input_file", str(APP_DIR / "tag_input.txt")),
            default_delay=self.settings.get("mark_delay", 1.5),
            default_simulation=sim_mode,
            on_launch_ezcad=self._launch_or_focus_ezcad,
            on_red_light=self._trigger_red_light,
            on_simulation_toggle=self._toggle_simulation_mode,
        )
        self.ezcad_comp.pack(fill="x", pady=(0, 6))

        # 4. RFID Tag & Duplicate Filter Panel
        self.rfid_comp = RfidDuplicatePanel(
            self.main_container,
            default_interval=1.5,
            default_strict_duplicate=self.settings.get("strict_duplicate", True),
            on_read_tag=self._trigger_read_tag,
            on_toggle_auto_read=self._toggle_auto_read,
            on_view_history=self._view_history_dialog,
            on_clear_history=self._clear_history_action,
        )
        self.rfid_comp.prefix_var.set(self.settings.get("tag_prefix", ""))
        self.rfid_comp.pack(fill="x", pady=(0, 6))

        # 5. Laser Actions & Hardware Feedback Panel
        self.action_comp = ActionPanel(
            self.main_container,
            on_write_file=self._update_input_file_only,
            on_mark=self._trigger_manual_mark,
            on_auto_pipeline_toggle=self._toggle_auto_pipeline,
            on_stop=self._stop_marking,
        )
        self.action_comp.pack(fill="x", pady=(0, 6))

        # 6. Activity & Diagnostic Log Panel
        self.log_comp = LogPanel(self.main_container)
        self.log_comp.pack(fill="both", expand=True)

        self.log_comp.log("RFID Laser Controller (EzCAD GUI Automation) initialized.", level="SUCCESS")
        self.log_comp.log(f"Working Directory: {APP_DIR}", level="INFO")
        self.log_comp.log(f"Loaded {self.duplicate_filter.unique_marked_count} marked tags from history database.", level="INFO")

    def _sync_statistics(self):
        stats = self.duplicate_filter.get_statistics()
        self.rfid_comp.update_statistics(
            scanned=stats["scanned"],
            marked=stats["marked"],
            duplicates=stats["duplicates"],
        )

    # -------------------------------------------------------------------------
    # Serial Port Methods
    # -------------------------------------------------------------------------
    def _connect_serial(self, port: str, baud: int):
        self.log_comp.log(f"Connecting to RFID reader on {port} at {baud} baud...", level="INFO")
        success = self.reader.connect(port=port, baudrate=baud)
        if success:
            self.comm_comp.set_connected_state(True)
            self.settings["port"] = port
            self.settings["baudrate"] = baud
            save_gui_settings(self.settings)
            self.log_comp.log(f"Serial port {port} connected successfully.", level="SUCCESS")
        else:
            self.comm_comp.set_connected_state(False)
            self.log_comp.log(f"Failed to connect to serial port {port}.", level="ERROR")
            messagebox.showerror("Connection Error", f"Could not open serial port {port}.")

    def _disconnect_serial(self):
        self._toggle_auto_read(False, 1.5)
        self.reader.disconnect()
        self.comm_comp.set_connected_state(False)
        self.log_comp.log("Serial port disconnected.", level="INFO")

    def _on_reader_disconnected(self):
        self.root.after(0, lambda: self.comm_comp.set_connected_state(False))
        self.root.after(0, lambda: self.log_comp.log("RFID reader disconnected asynchronously.", level="WARNING"))

    def _trigger_read_tag(self):
        if self.is_marking:
            return

        if not self.reader.is_connected():
            self.log_comp.log("Cannot read tag: Serial reader is not connected.", level="WARNING")
            return

        self.rfid_comp.set_duplicate_status("READING")
        self.log_comp.log(f"TX -> RFID: Read Tag ID command [{READ_TAG_ID_CMD.hex(' ').upper()}]", level="INFO")
        self.reader.write_bytes(READ_TAG_ID_CMD)

    def _toggle_auto_read(self, active: bool, interval_sec: float):
        self.is_auto_reading = active
        if self.auto_read_timer_id:
            self.root.after_cancel(self.auto_read_timer_id)
            self.auto_read_timer_id = None

        if active:
            self.log_comp.log(f"Auto-read started (Interval: {interval_sec}s)", level="INFO")
            self._auto_read_tick(interval_sec)
        else:
            self.log_comp.log("Auto-read stopped.", level="INFO")

    def _auto_read_tick(self, interval_sec: float):
        if not self.is_auto_reading:
            return
        if self.reader.is_connected() and not self.is_marking:
            self._trigger_read_tag()
        delay_ms = int(interval_sec * 1000)
        self.auto_read_timer_id = self.root.after(delay_ms, lambda: self._auto_read_tick(interval_sec))

    def _poll_serial(self):
        """Asynchronously read serial byte batches from the queue."""
        try:
            batch = self.reader.get_raw_batch(max_items=30)
            for chunk in batch:
                self.rx_buffer.extend(chunk)

            if len(self.rx_buffer) > 4096:
                del self.rx_buffer[:-1024]

            while len(self.rx_buffer) >= 5:
                if 0x24 in self.rx_buffer:
                    idx = self.rx_buffer.index(0x24)
                    if idx > 0:
                        del self.rx_buffer[:idx]
                else:
                    self.rx_buffer.clear()
                    break

                if len(self.rx_buffer) < 5:
                    break

                length_byte = self.rx_buffer[2]
                candidate_lengths = [length_byte + 4, length_byte + 6, length_byte + 5, length_byte + 7]
                frame_found = False

                for exp_len in candidate_lengths:
                    if exp_len >= 5 and len(self.rx_buffer) >= exp_len:
                        if self.rx_buffer[exp_len - 1] == 0x23:
                            frame = bytes(self.rx_buffer[:exp_len])
                            del self.rx_buffer[:exp_len]
                            self._process_rfid_frame(frame)
                            frame_found = True
                            break

                if frame_found:
                    continue

                min_exp = min(candidate_lengths)
                if len(self.rx_buffer) < min_exp:
                    break

                try:
                    next_start = self.rx_buffer.index(0x24, 1)
                    del self.rx_buffer[:next_start]
                except ValueError:
                    del self.rx_buffer[:-1]
                    break

        except Exception as e:
            self.log_comp.log(f"Error in serial poll loop: {e}", level="ERROR")
        finally:
            self.root.after(40, self._poll_serial)

    def _process_rfid_frame(self, frame: bytes):
        """Decode RFID frame and handle duplicate verification."""
        frame_hex = frame.hex(" ").upper()
        self.log_comp.log(f"RX <- RFID: [{frame_hex}]", level="INFO")

        success, tag_id, msg = parse_rfid_response_frame(frame)

        if success and tag_id:
            self.rfid_comp.set_tag_value(tag_id)
            self.last_scanned_tag = tag_id
            self.log_comp.log(f"Decoded Tag ID: {tag_id}", level="SUCCESS")

            # Check Duplicate Prevention
            is_strict = self.rfid_comp.is_strict_duplicate_enabled()
            is_dup = self.duplicate_filter.is_duplicate(tag_id)

            if is_dup and is_strict:
                self.rfid_comp.set_duplicate_status("DUPLICATE", tag_id)
                self.action_comp.set_marking_state(
                    False,
                    f"⚠️ DUPLICATE DETECTED: {tag_id} — ALREADY MARKED (SKIPPED)",
                    level="WARNING",
                )
                self.duplicate_filter.duplicates_blocked_count += 1
                self.duplicate_filter.total_scanned_count += 1
                self._sync_statistics()
                self.log_comp.log(
                    f"DUPLICATE BLOCKED: Tag '{tag_id}' has already been marked! Marking skipped to prevent duplication.",
                    level="WARNING",
                )
                # If pipeline active, wait and poll for the next tag
                if self.is_pipeline_active:
                    self._schedule_pipeline_next(delay_sec=1.5)
            else:
                self.rfid_comp.set_duplicate_status("UNIQUE", tag_id)
                self.log_comp.log(f"New Unique Tag verified: {tag_id}. Ready to mark.", level="SUCCESS")

                # If continuous pipeline is active, fire mark immediately!
                if self.is_pipeline_active:
                    self.root.after(100, lambda: self._execute_mark_workflow(tag_id))
        else:
            self.rfid_comp.set_duplicate_status("WAITING")
            self.log_comp.log(f"Tag read response: {msg}", level="WARNING")
            if self.is_pipeline_active:
                self._schedule_pipeline_next(delay_sec=1.0)

    # -------------------------------------------------------------------------
    # EzCAD GUI & Automation Actions
    # -------------------------------------------------------------------------
    def _launch_or_focus_ezcad(self):
        exe_path = self.ezcad_comp.get_ezcad_exe_path()
        tmpl_path = self.ezcad_comp.get_template_path()

        if self.ezcad_controller.is_ezcad_running():
            focused = self.ezcad_controller.focus_ezcad()
            if focused:
                self.log_comp.log("EzCAD window brought to foreground.", level="SUCCESS")
            else:
                self.log_comp.log("EzCAD is running but could not be brought to front.", level="WARNING")
        else:
            self.log_comp.log(f"Launching EzCAD: {exe_path} with template {tmpl_path}...", level="INFO")
            ok, msg = self.ezcad_controller.launch_ezcad(exe_path, tmpl_path)
            if ok:
                self.log_comp.log(msg, level="SUCCESS")
            else:
                self.log_comp.log(msg, level="ERROR")
                messagebox.showerror("EzCAD Launch Error", msg)

    def _trigger_red_light(self):
        sim = self.ezcad_comp.is_simulation()
        ok, msg = self.ezcad_controller.trigger_red_light(simulation_mode=sim)
        self.log_comp.log(msg, level="INFO" if ok else "ERROR")

    def _update_input_file_only(self):
        tag_val = self.rfid_comp.get_full_formatted_tag()
        if not tag_val:
            messagebox.showwarning("Empty Tag", "Please scan or enter a Tag ID first.")
            return

        input_file = self.ezcad_comp.get_input_file_path()
        ok, msg = self.ezcad_controller.write_tag_to_input_file(tag_val, input_file)
        if ok:
            self.log_comp.log(msg, level="SUCCESS")
        else:
            self.log_comp.log(msg, level="ERROR")

    def _trigger_manual_mark(self):
        tag_val = self.rfid_comp.get_full_formatted_tag()
        if not tag_val:
            messagebox.showwarning("Empty Tag", "Please scan or enter a Tag ID first.")
            return

        # Check duplicate
        if self.rfid_comp.is_strict_duplicate_enabled() and self.duplicate_filter.is_duplicate(tag_val):
            messagebox.showwarning(
                "Duplicate Tag",
                f"Tag '{tag_val}' has ALREADY been marked in this database!\n\n"
                "Marking is blocked to prevent double-marking. Present a new tag.",
            )
            return

        self._execute_mark_workflow(tag_val)

    def _execute_mark_workflow(self, tag_id: str):
        """Execute full marking workflow:
        1. Write Tag ID to dynamic input text file
        2. Focus EzCAD window
        3. Send F2 hotkey to fire laser
        4. Wait for marking duration
        5. Record into duplicate database
        6. Display hardware feedback OK
        """
        if self.is_marking:
            return

        self.is_marking = True
        self.action_comp.set_marking_state(True, "⏳ LASER MARKING IN PROGRESS (F2 ACTIVE)... WAITING FOR COMPLETION")

        prefix = self.rfid_comp.get_prefix()
        full_tag = f"{prefix}{tag_id}" if prefix else tag_id
        input_file = self.ezcad_comp.get_input_file_path()
        mark_delay = self.ezcad_comp.get_mark_delay()
        sim_mode = self.ezcad_comp.is_simulation()

        self.log_comp.log(f"Initiating mark for Tag '{full_tag}' (Input File: {Path(input_file).name}, Settle: {mark_delay}s)...", level="HIGHLIGHT")

        def _worker():
            try:
                ok, msg, duration = self.ezcad_controller.trigger_mark(
                    tag_id=full_tag,
                    input_file=input_file,
                    mark_delay_sec=mark_delay,
                    simulation_mode=sim_mode,
                )

                def _ui_done():
                    self.is_marking = False
                    if ok:
                        # Record in duplicate filter
                        self.duplicate_filter.check_and_record(tag_id, duration)
                        self._sync_statistics()

                        self.action_comp.set_marking_state(
                            False,
                            f"✅ JOB DONE (DURATION: {duration:.2f}s) — FEEDBACK: OK — READY FOR NEXT TAG",
                            level="SUCCESS",
                        )
                        self.log_comp.log(f"Mark completed successfully! {msg}", level="SUCCESS")

                        # If continuous pipeline is active, trigger reading next tag
                        if self.is_pipeline_active:
                            self.rfid_comp.clear_tag()
                            self.log_comp.log("[CONTINUOUS PIPELINE] Waiting 1.0s before reading next tag...", level="INFO")
                            self._schedule_pipeline_next(delay_sec=1.0)
                    else:
                        self.action_comp.set_marking_state(False, f"❌ MARKING FAILED — {msg}", level="ERROR")
                        self.log_comp.log(f"Marking failed: {msg}", level="ERROR")
                        if self.is_pipeline_active:
                            self.action_comp.stop_pipeline()
                            self.is_pipeline_active = False

                self.root.after(0, _ui_done)
            except Exception as exc:
                def _ui_err():
                    self.is_marking = False
                    self.action_comp.set_marking_state(False, f"❌ ERROR: {exc}", level="ERROR")
                    self.log_comp.log(f"Exception during mark execution: {exc}", level="ERROR")
                self.root.after(0, _ui_err)

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_auto_pipeline(self, active: bool):
        self.is_pipeline_active = active
        if active:
            self.log_comp.log("=== CONTINUOUS PRODUCTION PIPELINE STARTED ===", level="HIGHLIGHT")
            self.log_comp.log("Ready to scan tags. Unique tags will be marked automatically.", level="INFO")
            if self.reader.is_connected():
                self._trigger_read_tag()
            else:
                messagebox.showwarning("Reader Not Connected", "Please connect the RFID Reader first.")
                self.action_comp.stop_pipeline()
                self.is_pipeline_active = False
        else:
            self.log_comp.log("Continuous production pipeline stopped.", level="INFO")
            if self.pipeline_timer_id:
                self.root.after_cancel(self.pipeline_timer_id)
                self.pipeline_timer_id = None

    def _schedule_pipeline_next(self, delay_sec: float = 1.0):
        if not self.is_pipeline_active:
            return
        if self.pipeline_timer_id:
            self.root.after_cancel(self.pipeline_timer_id)
        self.pipeline_timer_id = self.root.after(
            int(delay_sec * 1000), self._trigger_read_tag
        )

    def _stop_marking(self):
        self._toggle_auto_pipeline(False)
        self._toggle_auto_read(False, 1.5)
        sim = self.ezcad_comp.is_simulation()
        ok, msg = self.ezcad_controller.trigger_stop(simulation_mode=sim)
        self.log_comp.log(f"Stop command: {msg}", level="WARNING")
        self.is_marking = False
        self.action_comp.set_marking_state(False, "⏹ LASER STOPPED BY OPERATOR", level="WARNING")

    def _toggle_simulation_mode(self, is_sim: bool):
        self.settings["simulation_mode"] = is_sim
        self.header_comp.update_mode(is_sim)
        save_gui_settings(self.settings)
        mode_str = "SIMULATION" if is_sim else "HARDWARE (EZCAD GUI)"
        self.log_comp.log(f"Operating mode switched to: {mode_str}", level="INFO")

    # -------------------------------------------------------------------------
    # History Dialogs
    # -------------------------------------------------------------------------
    def _view_history_dialog(self):
        records = self.duplicate_filter.get_recent_history(max_items=100)
        win = tk.Toplevel(self.root)
        win.title("Marked Tag History Database")
        win.geometry("560x420")
        win.transient(self.root)

        lbl = ttk.Label(
            win,
            text=f"Total Unique Tags Marked: {self.duplicate_filter.unique_marked_count} (Showing last {len(records)})",
            font=("Segoe UI", 10, "bold"),
            padding=10,
        )
        lbl.pack(anchor="w")

        cols = ("Timestamp", "Tag ID", "Duration (s)")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=15)
        tree.heading("Timestamp", text="Timestamp")
        tree.heading("Tag ID", text="Tag ID")
        tree.heading("Duration (s)", text="Duration")
        tree.column("Timestamp", width=160)
        tree.column("Tag ID", width=260)
        tree.column("Duration (s)", width=90)

        for rec in reversed(records):
            tree.insert("", "end", values=(rec.get("timestamp"), rec.get("tag_id"), rec.get("duration")))

        tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _clear_history_action(self):
        self.duplicate_filter.clear_history()
        self._sync_statistics()
        self.rfid_comp.clear_tag()
        self.log_comp.log("Marked tag history cleared and archived.", level="WARNING")
        messagebox.showinfo("History Cleared", "Marked tag history has been cleared and archived.")

    def _on_close(self):
        self._toggle_auto_read(False, 1.5)
        self._toggle_auto_pipeline(False)
        if self.reader:
            self.reader.disconnect()

        self.settings["port"] = self.comm_comp.get_port()
        self.settings["baudrate"] = self.comm_comp.get_baud()
        self.settings["ezcad_exe"] = self.ezcad_comp.get_ezcad_exe_path()
        self.settings["ezd_template"] = self.ezcad_comp.get_template_path()
        self.settings["input_file"] = self.ezcad_comp.get_input_file_path()
        self.settings["mark_delay"] = self.ezcad_comp.get_mark_delay()
        self.settings["strict_duplicate"] = self.rfid_comp.is_strict_duplicate_enabled()
        self.settings["simulation_mode"] = self.ezcad_comp.is_simulation()
        self.settings["tag_prefix"] = self.rfid_comp.get_prefix()
        save_gui_settings(self.settings)

        self.root.destroy()

    def run(self):
        self.root.mainloop()
