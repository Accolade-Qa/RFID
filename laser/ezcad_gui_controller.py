"""EzCAD 2.x GUI Automation Controller via PyAutoGUI, Win32 API, and Dynamic Text File Binding.
Automates EzCAD application: updates tag_input.txt -> brings EzCAD to front -> triggers Mark (F2).
Uses PyAutoGUI for reliable keypress automation, with native Win32 API fallbacks.
Bypasses DLL vendor dongle authorization errors by utilizing the licensed EzCAD standalone GUI.
"""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except Exception:
    gw = None
    HAS_PYGETWINDOW = False


# Virtual Key Codes & Mappings
VK_F1 = 0x70       # EzCAD Red Light / Guide Box
VK_F2 = 0x71       # EzCAD Mark Command
VK_ESCAPE = 0x1B   # EzCAD Stop / Abort Mark
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9
SW_SHOW = 5

VK_TO_KEY_NAME: Dict[int, str] = {
    VK_F1: "f1",
    VK_F2: "f2",
    VK_ESCAPE: "escape",
}

KEY_NAME_TO_VK: Dict[str, int] = {
    "f1": VK_F1,
    "f2": VK_F2,
    "esc": VK_ESCAPE,
    "escape": VK_ESCAPE,
}


def auto_detect_ezcad_exe() -> Optional[Path]:
    """Search for EzCad2.exe across known system paths, Downloads, and standard installation directories."""
    user_home = Path.home()
    candidates = [
        user_home / "Downloads" / "LASER MACHINE SETUP 1" / "LASER MACHINE SETUP" / "Software driver" / "Ezcad2.14.11" / "EzCad2.exe",
        user_home / "Downloads" / "LASER MACHINE SETUP 1" / "LASER MACHINE SETUP" / "20260518SN817DC-355-312698" / "20260518SN817DC-355-312698" / "Ezcad2.14.11" / "EzCad2.exe",
        Path("C:/EzCad2/EzCad2.exe"),
        Path("C:/EzCad2/Ezcad.exe"),
        Path("C:/Ezcad2.14.11/EzCad2.exe"),
        Path("C:/EzCad/Ezcad.exe"),
        Path("D:/EzCad2/EzCad2.exe"),
        Path("D:/EzCad2/Ezcad.exe"),
    ]

    for cand in candidates:
        if cand.is_file():
            return cand

    # Search user's Downloads and Desktop directories
    for search_dir in [user_home / "Downloads", user_home / "Desktop"]:
        if search_dir.is_dir():
            try:
                for match in search_dir.glob("**/EzCad*.exe"):
                    if match.is_file() and not match.name.lower().startswith("ezcad_dev"):
                        return match
            except Exception:
                pass

    return None


class EzcadGuiController:
    """Controls the EzCAD GUI application, updates input files, and triggers laser marking via PyAutoGUI."""

    def __init__(self, ezcad_exe_path: str = "", input_file_path: str = "", template_path: str = ""):
        # If no valid path provided, attempt automatic detection
        if not ezcad_exe_path or not Path(ezcad_exe_path).is_file():
            detected = auto_detect_ezcad_exe()
            if detected:
                ezcad_exe_path = str(detected)

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
        """Find top-level window handle of the running EzCAD software."""
        # 1. Check with PyGetWindow if available
        if HAS_PYGETWINDOW and gw:
            try:
                for kw in ["ezcad", "EzCad", "EZCAD"]:
                    wins = gw.getWindowsWithTitle(kw)
                    for w in wins:
                        if w.visible and w._hWnd:
                            return w._hWnd
            except Exception:
                pass

        # 2. Native Win32 EnumWindows fallback
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
        # 1. Check by active window
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
        if exe_path:
            target_exe = Path(exe_path).resolve()
            if not target_exe.is_file():
                return False, f"EzCAD executable not found at: '{exe_path}'."
        else:
            exe_candidate = self.ezcad_exe_path
            if not exe_candidate or not Path(exe_candidate).is_file():
                detected = auto_detect_ezcad_exe()
                if detected:
                    exe_candidate = str(detected)
                    self.ezcad_exe_path = exe_candidate
                else:
                    return False, f"EzCAD executable not found at: '{exe_candidate}'. Please browse and select EzCad2.exe."
            target_exe = Path(exe_candidate).resolve()

        target_tmpl = Path(template_path or self.template_path).resolve() if (template_path or self.template_path) else None

        # If already open and visible, bring to front instead of duplicate launch
        if self.find_ezcad_window() is not None:
            self.focus_ezcad()
            return True, f"EzCAD is already open and has been brought to the foreground."

        # Launch EzCAD executable in its own working directory
        cwd = str(target_exe.parent)
        try:
            # 1. Try os.startfile (mimics double-clicking EzCad2.exe in Explorer)
            launched = False
            if hasattr(os, "startfile") and (not target_tmpl or not target_tmpl.is_file()):
                try:
                    orig_dir = os.getcwd()
                    os.chdir(cwd)
                    try:
                        os.startfile(str(target_exe))
                        launched = True
                    finally:
                        os.chdir(orig_dir)
                except Exception:
                    launched = False

            # 2. Fallback to subprocess.Popen
            if not launched:
                cmd = [str(target_exe)]
                if target_tmpl and target_tmpl.is_file():
                    cmd.append(str(target_tmpl))
                subprocess.Popen(cmd, cwd=cwd, shell=False)

            # Wait up to 3 seconds for window creation
            for _ in range(15):
                time.sleep(0.2)
                if self.find_ezcad_window() is not None:
                    break

            self.focus_ezcad()
            return True, f"EzCAD launched successfully: {target_exe.name}"
        except Exception as exc:
            return False, f"Failed to launch EzCAD from {target_exe}: {exc}"

    def focus_ezcad(self) -> bool:
        """Bring the EzCAD window to the foreground so it receives hotkeys."""
        # 1. Try PyGetWindow activation
        if HAS_PYGETWINDOW and gw:
            try:
                for kw in ["ezcad", "EzCad", "EZCAD"]:
                    windows = gw.getWindowsWithTitle(kw)
                    for win in windows:
                        if win.visible:
                            try:
                                if win.isMinimized:
                                    win.restore()
                                win.activate()
                                time.sleep(0.1)
                                return True
                            except Exception:
                                pass
            except Exception:
                pass

        # 2. Win32 API fallback
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

    def send_key(self, key: Any, vk_code: Optional[int] = None) -> bool:
        """Synthesize a hardware keypress using PyAutoGUI with Win32 fallback.
        Supports:
          - send_key('f2')
          - send_key(VK_F2)
          - send_key('f2', VK_F2)
        """
        key_name = ""
        vk = 0

        if isinstance(key, str):
            key_name = key.lower()
            vk = vk_code or KEY_NAME_TO_VK.get(key_name, 0)
        elif isinstance(key, int):
            vk = key
            key_name = VK_TO_KEY_NAME.get(vk, "")

        # 1. PyAutoGUI keypress
        if HAS_PYAUTOGUI and pyautogui and key_name:
            try:
                pyautogui.press(key_name)
                time.sleep(0.05)
                return True
            except Exception:
                pass

        # 2. Win32 keybd_event fallback
        if self.user32 and vk:
            try:
                self.user32.keybd_event(vk, 0, 0, 0)
                time.sleep(0.08)
                self.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
                return True
            except Exception:
                pass

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
        3. Send F2 hotkey via PyAutoGUI to fire laser
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
            launched, launch_msg = self.launch_ezcad()
            if not launched:
                return False, f"EzCAD is not open and could not be auto-launched: {launch_msg}", 0.0

        # Bring EzCAD to foreground
        focused = self.focus_ezcad()
        if not focused:
            time.sleep(0.3)
            self.focus_ezcad()

        # Small delay for EzCAD to finish reading file buffer
        time.sleep(0.15)

        # Synthesize F2 (EzCAD Mark shortcut) via PyAutoGUI
        key_ok = self.send_key("f2", VK_F2)
        if not key_ok:
            return False, "Failed to send F2 key to EzCAD.", 0.0

        # Wait for laser trajectory to complete
        settle_time = max(mark_delay_sec, 0.3)
        time.sleep(settle_time)

        duration = time.time() - t0
        self.last_mark_duration = duration

        return True, f"Laser marked tag '{tag_id}' via EzCAD (PyAutoGUI F2, Duration: {duration:.2f}s)", duration

    def trigger_stop(self, simulation_mode: bool = False) -> Tuple[bool, str]:
        """Send ESC to EzCAD to halt laser marking."""
        if simulation_mode:
            return True, "[SIMULATION] Marking stopped."
        self.focus_ezcad()
        self.send_key("escape", VK_ESCAPE)
        return True, "Stop command (ESC) sent to EzCAD."

    def trigger_red_light(self, simulation_mode: bool = False) -> Tuple[bool, str]:
        """Send F1 to EzCAD for Red Light contour preview."""
        if simulation_mode:
            return True, "[SIMULATION] Red light preview toggled."
        self.focus_ezcad()
        self.send_key("f1", VK_F1)
        return True, "Red Light preview command (F1) sent to EzCAD."
