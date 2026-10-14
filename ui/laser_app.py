"""Main Application Window for RFID Laser Marking Utility."""

import json
import os
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, Dict, Any

from communication.protocol import READ_TAG_ID_CMD, parse_rfid_response_frame
from communication.uart import SerialReader
from laser.ezcad_driver import BaseLaserDriver, create_laser_driver
from ui.laser_components.comm_panel import CommPanel
from ui.laser_components.header import HeaderComponent
from ui.laser_components.laser_panel import LaserPanel
from ui.laser_components.log_panel import LogPanel
from ui.laser_components.rfid_panel import RFIDPanel

def resolve_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

APP_DIR = resolve_app_dir()
SETTINGS_FILE = APP_DIR / "laser_settings.json"


DEFAULT_SETTINGS: Dict[str, Any] = {
    "port": "COM3",
    "baudrate": 115200,
    "ezcad_dir": str(APP_DIR),
    "ezd_template": str(APP_DIR / "test.ezd"),
    "text_entity_name": "t1",
    "tag_prefix": "",
    "simulation_mode": False,
    "auto_mark_on_read": False,
}


def load_laser_settings() -> Dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.is_file():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    settings.update(loaded)
        except Exception:
            pass
    return settings


def save_laser_settings(settings: Dict[str, Any]) -> bool:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception:
        return False


class RFIDLaserApp:
    """Master Application Window and Controller for RFID Laser Marking."""

    def __init__(self, root: Optional[tk.Tk] = None):
        self.root = root or tk.Tk()
        self.root.title("AEPL RFID Laser Marking Utility")
        self.root.geometry("840x760")
        self.root.minsize(720, 660)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.settings = load_laser_settings()

        self.reader = SerialReader(
            port=self.settings.get("port", "COM3"),
            baudrate=self.settings.get("baudrate", 115200),
        )
        self.reader.set_disconnect_callback(self._on_reader_disconnected)

        self.laser_driver: Optional[BaseLaserDriver] = None
        self.rx_buffer = bytearray()
        self.is_auto_reading = False
        self.auto_read_timer_id: Optional[str] = None
        self.pending_read_for_mark = False
        self.is_marking = False
        self.continuous_job_timer_id: Optional[str] = None

        self._build_ui()
        self._init_laser_driver()

        self.root.after(50, self._poll_serial)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.main_container = ttk.Frame(self.root, padding=10)
        self.main_container.pack(fill="both", expand=True)

        sim_mode = self.settings.get("simulation_mode", False)
        self.header_comp = HeaderComponent(self.main_container, is_simulation=sim_mode)
        self.header_comp.pack(fill="x", pady=(0, 6))

        self.comm_comp = CommPanel(
            self.main_container,
            default_port=self.settings.get("port", "COM3"),
            default_baud=self.settings.get("baudrate", 115200),
            on_connect=self._connect_serial,
            on_disconnect=self._disconnect_serial,
        )
        self.comm_comp.pack(fill="x", pady=(0, 6))

        self.rfid_comp = RFIDPanel(
            self.main_container,
            on_read_tag=self._trigger_read_tag,
            on_auto_read_toggle=self._toggle_auto_read,
            on_tag_changed=self._on_tag_text_changed,
        )
        self.rfid_comp.pack(fill="x", pady=(0, 6))

        default_template = self.settings.get("ezd_template", str(APP_DIR / "test.ezd"))
        default_ezcad_dir = self.settings.get("ezcad_dir", str(APP_DIR))
        default_entity = self.settings.get("text_entity_name", "t1")
        default_auto_mark = self.settings.get("auto_mark_on_read", False)

        self.laser_comp = LaserPanel(
            self.main_container,
            default_template=default_template,
            default_ezcad_dir=default_ezcad_dir,
            default_entity=default_entity,
            default_simulation=sim_mode,
            default_auto_mark=default_auto_mark,
            on_update_template=self._update_template_text,
            on_mark=self._trigger_mark,
            on_read_and_mark=self._trigger_read_and_mark_flow,
            on_stop_mark=self._stop_marking,
            on_simulation_toggle=self._toggle_simulation_mode,
        )
        self.laser_comp.pack(fill="x", pady=(0, 6))

        self.log_comp = LogPanel(self.main_container)
        self.log_comp.pack(fill="both", expand=True)

        self.log_comp.log("Application started successfully.", level="INFO")
        self.log_comp.log(f"Working Directory: {APP_DIR}", level="INFO")

    def _init_laser_driver(self):
        ezcad_dir = self.laser_comp.get_ezcad_dir()
        sim_mode = self.laser_comp.is_simulation()

        try:
            if self.laser_driver:
                self.laser_driver.close()

            self.laser_driver = create_laser_driver(ezcad_dir, simulation_mode=sim_mode)
            self.header_comp.update_mode(sim_mode)

            template_path = self.laser_comp.get_template_path()
            if os.path.isfile(template_path):
                self.laser_driver.load_template(template_path)
                entities = self.laser_driver.list_entities()
                mode_str = "SIMULATION" if sim_mode else "HARDWARE"
                self.log_comp.log(
                    f"EzCAD [{mode_str}] initialized. Template loaded: {Path(template_path).name} (Entities: {entities})",
                    level="SUCCESS",
                )
            else:
                self.log_comp.log(
                    f"Template not found at: {template_path}. Please select a valid .ezd file.",
                    level="WARNING",
                )
        except Exception as e:
            self.log_comp.log(f"Failed to initialize EzCAD driver: {e}", level="ERROR")

    def _connect_serial(self, port: str, baud: int):
        self.log_comp.log(f"Connecting to RFID reader on {port} at {baud} baud...", level="INFO")
        success = self.reader.connect(port=port, baudrate=baud)
        if success:
            self.comm_comp.set_connected_state(True)
            self.settings["port"] = port
            self.settings["baudrate"] = baud
            save_laser_settings(self.settings)
            self.log_comp.log(f"Serial port {port} connected.", level="SUCCESS")
        else:
            self.comm_comp.set_connected_state(False)
            self.log_comp.log(f"Failed to connect to serial port {port}.", level="ERROR")
            messagebox.showerror("Connection Error", f"Could not open serial port {port}.")

    def _disconnect_serial(self):
        self._toggle_auto_read(False, 2.0)
        self.reader.disconnect()
        self.comm_comp.set_connected_state(False)
        self.log_comp.log("Serial port disconnected.", level="INFO")

    def _on_reader_disconnected(self):
        self.root.after(0, lambda: self.comm_comp.set_connected_state(False))
        self.root.after(0, lambda: self.log_comp.log("RFID reader disconnected asynchronously.", level="WARNING"))

    def _trigger_read_tag(self):
        if self.is_marking:
            self.log_comp.log("Laser marking is in progress. Waiting for hardware completion before reading next tag.", level="WARNING")
            return

        if not self.reader.is_connected():
            self.log_comp.log("Cannot read tag: Serial reader is not connected.", level="WARNING")
            self.rfid_comp.set_reading_state(False, msg="Reader disconnected")
            return


        self.rfid_comp.set_reading_state(True, msg="Reading...")
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
        if self.reader.is_connected():
            self._trigger_read_tag()
        delay_ms = int(interval_sec * 1000)
        self.auto_read_timer_id = self.root.after(delay_ms, lambda: self._auto_read_tick(interval_sec))

    def _on_tag_text_changed(self, new_val: str):
        pass

    def _poll_serial(self):
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
        frame_hex = frame.hex(" ").upper()
        self.log_comp.log(f"RX <- RFID: [{frame_hex}]", level="INFO")

        success, tag_id, msg = parse_rfid_response_frame(frame)
        self.rfid_comp.set_reading_state(False)

        if success and tag_id:
            self.rfid_comp.set_tag_value(tag_id)
            self.log_comp.log(f"Tag ID decoded: {tag_id}", level="SUCCESS")

            auto_mark = self.laser_comp.is_auto_mark_enabled()
            if auto_mark or self.pending_read_for_mark:
                self.pending_read_for_mark = False
                self.root.after(100, self._perform_update_and_mark)
        else:
            self.log_comp.log(f"Tag read failed: {msg}", level="WARNING")
            if self.pending_read_for_mark:
                self.pending_read_for_mark = False
                self.log_comp.log("Auto-flow aborted: Tag could not be read.", level="ERROR")

    def _update_template_text(self, entity_name: str, prefix: str) -> bool:
        raw_tag = self.rfid_comp.get_tag_value()
        if not raw_tag:
            self.log_comp.log("Cannot update template: Tag ID input is empty.", level="WARNING")
            messagebox.showwarning("Empty Tag", "Please enter or scan a Tag ID first.")
            return False

        if not self.laser_driver or not self.laser_driver.is_initialized():
            self._init_laser_driver()
            if not self.laser_driver or not self.laser_driver.is_initialized():
                self.log_comp.log("EzCAD laser driver is not ready.", level="ERROR")
                return False

        combined_text = f"{prefix}{raw_tag}" if prefix else raw_tag
        self.log_comp.log(f"Updating entity '{entity_name}' with value '{combined_text}'...", level="INFO")

        ok, result_msg = self.laser_driver.change_text(entity_name, combined_text)
        if ok:
            self.log_comp.log(result_msg, level="SUCCESS")
            return True
        else:
            self.log_comp.log(result_msg, level="ERROR")
            messagebox.showerror("EzCAD Error", result_msg)
            return False

    def _trigger_mark(self, on_complete: Optional[Any] = None):
        if self.is_marking:
            self.log_comp.log("Laser is already in progress. Please wait for current job to complete.", level="WARNING")
            return

        if not self.laser_driver or not self.laser_driver.is_initialized():
            self._init_laser_driver()
            if not self.laser_driver or not self.laser_driver.is_initialized():
                self.log_comp.log("Cannot mark: EzCAD driver not initialized.", level="ERROR")
                return

        self.is_marking = True
        self.laser_comp.set_marking_state(True, "⏳ LASER MARKING IN PROGRESS... WAITING FOR HARDWARE FEEDBACK")
        self.log_comp.log("Firing laser mark... Waiting for LMC1 hardware completion feedback.", level="HIGHLIGHT")

        def _worker():
            try:
                ok, msg = self.laser_driver.mark(fly_mark=False)
                duration = self.laser_driver.get_last_mark_duration()

                def _handle_ui_done():
                    self.is_marking = False
                    if ok:
                        self.laser_comp.set_marking_state(
                            False,
                            f"✅ JOB DONE ({duration:.2f}s) — FEEDBACK: OK — READY FOR NEXT",
                            level="SUCCESS",
                        )
                        self.laser_comp.record_job_completed(duration)
                        self.log_comp.log(f"Laser feedback received: SUCCESS! {msg}", level="SUCCESS")

                        if callable(on_complete):
                            on_complete(True)

                        # Continuous Pipeline: Auto-trigger next tag upon feedback
                        if self.laser_comp.is_continuous_enabled():
                            delay = self.laser_comp.get_next_job_delay()
                            self.log_comp.log(
                                f"[CONTINUOUS PIPELINE] Job done. Waiting {delay:.1f}s before reading next tag...",
                                level="INFO",
                            )
                            self.rfid_comp.clear_tag()
                            if self.continuous_job_timer_id:
                                self.root.after_cancel(self.continuous_job_timer_id)
                            self.continuous_job_timer_id = self.root.after(
                                int(delay * 1000), self._trigger_continuous_next
                            )
                    else:
                        self.laser_comp.set_marking_state(
                            False,
                            f"❌ MARKING FAILED — {msg}",
                            level="ERROR",
                        )
                        self.log_comp.log(f"Laser feedback received: FAILURE! {msg}", level="ERROR")
                        if callable(on_complete):
                            on_complete(False)

                self.root.after(0, _handle_ui_done)
            except Exception as e:
                def _handle_ui_err():
                    self.is_marking = False
                    self.laser_comp.set_marking_state(False, f"❌ EXCEPTION: {e}", level="ERROR")
                    self.log_comp.log(f"Mark execution exception: {e}", level="ERROR")
                    if callable(on_complete):
                        on_complete(False)
                self.root.after(0, _handle_ui_err)

        threading.Thread(target=_worker, daemon=True).start()

    def _trigger_continuous_next(self):
        """Callback invoked when laser completes and continuous pipeline is enabled."""
        if not self.laser_comp.is_continuous_enabled():
            return
        if self.is_marking:
            return
        self.log_comp.log("=== Continuous Pipeline: Scanning Next RFID Tag ===", level="HIGHLIGHT")
        self.pending_read_for_mark = True
        self._trigger_read_tag()

    def _perform_update_and_mark(self):
        entity = self.laser_comp.get_entity_name()
        prefix = self.laser_comp.get_prefix()
        if self._update_template_text(entity, prefix):
            self._trigger_mark()


    def _trigger_read_and_mark_flow(self):
        self.log_comp.log("=== Initiating One-Click Read & Mark Flow ===", level="HIGHLIGHT")
        if not self.reader.is_connected():
            self.log_comp.log("Serial reader is not connected. Connect reader first.", level="WARNING")
            messagebox.showwarning("Connection Required", "Please connect the RFID Reader first.")
            return

        self.pending_read_for_mark = True
        self._trigger_read_tag()

    def _stop_marking(self):
        if self.continuous_job_timer_id:
            self.root.after_cancel(self.continuous_job_timer_id)
            self.continuous_job_timer_id = None
        self.pending_read_for_mark = False
        if self.laser_driver:
            self.laser_driver.stop_mark()
            self.log_comp.log("Stop marking command issued to laser controller.", level="WARNING")
        self.is_marking = False
        self.laser_comp.set_marking_state(False, "⏹ LASER STOPPED BY OPERATOR", level="WARNING")


    def _toggle_simulation_mode(self, is_sim: bool):
        self.settings["simulation_mode"] = is_sim
        save_laser_settings(self.settings)
        self._init_laser_driver()

    def _on_close(self):
        self._toggle_auto_read(False, 2.0)
        if self.reader:
            self.reader.disconnect()
        if self.laser_driver:
            self.laser_driver.close()

        self.settings["ezd_template"] = self.laser_comp.get_template_path()
        self.settings["ezcad_dir"] = self.laser_comp.get_ezcad_dir()
        self.settings["text_entity_name"] = self.laser_comp.get_entity_name()
        self.settings["auto_mark_on_read"] = self.laser_comp.is_auto_mark_enabled()
        self.settings["simulation_mode"] = self.laser_comp.is_simulation()
        save_laser_settings(self.settings)

        self.root.destroy()

    def run(self):
        self.root.mainloop()
