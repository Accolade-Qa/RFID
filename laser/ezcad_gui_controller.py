"""EzCAD 2.x GUI Automation Controller via Win32 API and Dynamic Text File Binding.
Automates EzCAD application: updates tag_input.txt -> brings EzCAD to front -> triggers Mark (F2).
Bypasses DLL vendor dongle authorization errors by utilizing the licensed EzCAD standalone GUI.
"""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import time
from typing import List, Optional, Tuple


# Virtual Key Codes
VK_F1 = 0x70       # EzCAD Red Light / Guide Box
VK_F2 = 0x71       # EzCAD Mark Command
VK_ESCAPE = 0x1B   # EzCAD Stop / Abort Mark
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9
SW_SHOW = 5


class EzcadGuiController:
    """Controls the EzCAD GUI application, updates input files, and triggers laser marking."""

    def __init__(self, ezcad_exe_path: str = "", input_file_path: str = "", template_path: str = ""):
        self.ezcad_exe_path = ezcad_exe_path
        self.input_file_path = input_file_path
        self.template_path = template_path
        self.last_mark_duration: float = 0.0

        self.user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

    def write_tag_to_input_file(self, tag_id: str, file_path: Optional[str] = None) -> Tuple[bool, str]:
        """Write the scanned Tag ID to the input text file that EzCAD is configured to read."""
        target_path = Path(file_path or self.input_file_path).resolve()
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # Write single clean line with no trailing garbage
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(f"{tag_id.strip()}\n")
            return True, f"Updated laser input file: {target_path} -> '{tag_id.strip()}'"
        except Exception as exc:
            return False, f"Failed to write input file {target_path}: {exc}"

    def read_current_input_file(self, file_path: Optional[str] = None) -> str:
        """Read current content of the input text file."""
        target_path = Path(file_path or self.input_file_path).resolve()
        if target_path.is_file():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
        return ""

    def find_ezcad_window(self) -> Optional[int]:
        """Find the top-level window handle of the running EzCAD software."""
        if not self.user32:
            return None

        found_hwnds: List[int] = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @WNDENUMPROC
        def _enum_callback(hwnd, lparam):
            if self.user32.IsWindowVisible(hwnd):
                length = self.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    self.user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.lower()
                    if "ezcad" in title:
                        found_hwnds.append(hwnd)
            return True

        try:
            self.user32.EnumWindows(_enum_callback, 0)
        except Exception:
            pass

        return found_hwnds[0] if found_hwnds else None

    def is_ezcad_running(self) -> bool:
        """Check if EzCAD application is currently open."""
        # 1. Check by window title
        if self.find_ezcad_window() is not None:
            return True

        # 2. Check by process list
        try:
            out = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=2).stdout.lower()
            return "ezcad" in out
        except Exception:
            return False

    def launch_ezcad(self, exe_path: Optional[str] = None, template_path: Optional[str] = None) -> Tuple[bool, str]:
        """Launch the EzCAD application with the specified template if not already running."""
        target_exe = Path(exe_path or self.ezcad_exe_path).resolve()
        target_tmpl = Path(template_path or self.template_path).resolve() if (template_path or self.template_path) else None

        if not target_exe.is_file():
            return False, f"EzCAD executable not found at: {target_exe}"

        cmd = [str(target_exe)]
        if target_tmpl and target_tmpl.is_file():
            cmd.append(str(target_tmpl))

        try:
            subprocess.Popen(cmd, cwd=str(target_exe.parent))
            # Allow time for window creation
            time.sleep(1.5)
            return True, f"EzCAD launched successfully from: {target_exe.name}"
        except Exception as exc:
            return False, f"Failed to launch EzCAD: {exc}"

    def focus_ezcad(self) -> bool:
        """Bring the EzCAD window to the foreground so it receives hotkeys."""
        if not self.user32:
            return False

        hwnd = self.find_ezcad_window()
        if not hwnd:
            return False

        try:
            self.user32.ShowWindow(hwnd, SW_RESTORE)

            # Attach thread input to bypass Windows foreground restrictions
            fore_hwnd = self.user32.GetForegroundWindow()
            fore_thread = self.user32.GetWindowThreadProcessId(fore_hwnd, None)
            curr_thread = self.user32.GetWindowThreadProcessId(hwnd, None)

            if fore_thread != curr_thread:
                self.user32.AttachThreadInput(fore_thread, curr_thread, True)
                self.user32.SetForegroundWindow(hwnd)
                self.user32.AttachThreadInput(fore_thread, curr_thread, False)
            else:
                self.user32.SetForegroundWindow(hwnd)

            self.user32.BringWindowToTop(hwnd)
            self.user32.SetFocus(hwnd)
            time.sleep(0.1)
            return True
        except Exception:
            return False

    def send_key(self, vk_code: int) -> bool:
        """Synthesize a hardware keypress (keydown then keyup)."""
        if not self.user32:
            return False
        try:
            self.user32.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.08)
            self.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
            return True
        except Exception:
            return False

    def trigger_mark(
        self,
        tag_id: str,
        input_file: Optional[str] = None,
        mark_delay_sec: float = 1.5,
        simulation_mode: bool = False,
    ) -> Tuple[bool, str, float]:
        """Complete marking workflow:
        1. Write Tag ID to dynamic input text file
        2. Focus EzCAD window
        3. Send F2 hotkey to fire laser
        4. Wait for marking completion
        """
        t0 = time.time()

        # Step 1: Update input file for EzCAD
        target_file = input_file or self.input_file_path
        ok, msg = self.write_tag_to_input_file(tag_id, target_file)
        if not ok:
            return False, msg, 0.0

        # Step 2: Handle Simulation Mode
        if simulation_mode:
            time.sleep(max(mark_delay_sec, 0.5))
            duration = time.time() - t0
            self.last_mark_duration = duration
            return True, f"[SIMULATION] Updated '{Path(target_file).name}' -> '{tag_id}'. Mark simulated in {duration:.2f}s (Feedback: OK)", duration

        # Step 3: Hardware Marking via EzCAD GUI
        if not self.is_ezcad_running():
            # Try to launch EzCAD automatically
            launched, launch_msg = self.launch_ezcad()
            if not launched:
                return False, f"EzCAD is not open and could not be auto-launched: {launch_msg}", 0.0

        # Bring EzCAD to foreground
        focused = self.focus_ezcad()
        if not focused:
            # Try once more after slight delay
            time.sleep(0.3)
            self.focus_ezcad()

        # Small delay for EzCAD to finish reading file buffer
        time.sleep(0.15)

        # Synthesize F2 (EzCAD Mark shortcut)
        key_ok = self.send_key(VK_F2)
        if not key_ok:
            return False, "Failed to send F2 key to EzCAD.", 0.0

        # Wait for laser trajectory to complete
        settle_time = max(mark_delay_sec, 0.3)
        time.sleep(settle_time)

        duration = time.time() - t0
        self.last_mark_duration = duration

        return True, f"Laser marked tag '{tag_id}' via EzCAD (F2 Hotkey, Duration: {duration:.2f}s)", duration

    def trigger_stop(self, simulation_mode: bool = False) -> Tuple[bool, str]:
        """Send ESC to EzCAD to halt laser marking."""
        if simulation_mode:
            return True, "[SIMULATION] Marking stopped."
        self.focus_ezcad()
        self.send_key(VK_ESCAPE)
        return True, "Stop command (ESC) sent to EzCAD."

    def trigger_red_light(self, simulation_mode: bool = False) -> Tuple[bool, str]:
        """Send F1 to EzCAD for Red Light contour preview."""
        if simulation_mode:
            return True, "[SIMULATION] Red light preview toggled."
        self.focus_ezcad()
        self.send_key(VK_F1)
        return True, "Red Light preview command (F1) sent to EzCAD."
