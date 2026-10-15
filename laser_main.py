"""Standalone Launcher for AEPL RFID Laser Marking Utility with Crash Diagnostics.
Connects RFID Reader -> reads Tag ID -> updates text 't1' in EzCAD template 'test.ezd' -> marks laser.
Compatible with Windows 7 32-bit and Python 3.8 32-bit.
"""

from datetime import datetime
import os
from pathlib import Path
import struct
import subprocess
import sys
import traceback
from typing import Tuple

def resolve_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

PROJECT_ROOT = resolve_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


CRASH_LOG = PROJECT_ROOT / "crash.log"
ACTIVITY_LOG = PROJECT_ROOT / "activity.log"


def log_to_file(msg: str):
    """Write timestamped log to activity.log."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch-all for any unhandled exceptions to ensure visibility into crashes."""
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    error_msg = f"UNHANDLED FATAL EXCEPTION:\n{tb_str}"

    print(error_msg, file=sys.stderr)
    log_to_file(error_msg)

    # Write to crash.log
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"=== CRASH AT {ts} ===\n{tb_str}\n\n")
    except Exception:
        pass

    # Display pop-up error dialog if GUI is available
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Fatal Application Error",
            f"The application encountered an unexpected error:\n\n{exc_value}\n\n"
            f"A detailed crash report has been saved to:\n{CRASH_LOG}"
        )
        root.destroy()
    except Exception:
        pass

    sys.exit(1)


sys.excepthook = global_exception_handler


def get_system_architecture() -> Tuple[str, str]:
    """Detect PC Operating System architecture (32-bit vs 64-bit) and current process architecture."""
    is_64_os = False
    if sys.platform == "win32":
        if (
            os.environ.get("PROCESSOR_ARCHITECTURE") == "AMD64"
            or os.environ.get("PROCESSOR_ARCHITEW6432") == "AMD64"
        ):
            is_64_os = True
    os_arch = "64-bit (x64)" if is_64_os else "32-bit (x86)"
    proc_arch = f"{struct.calcsize('P') * 8}-bit"
    return os_arch, proc_arch


def check_and_relaunch_for_32bit() -> bool:
    """If running in 64-bit Python on a 64-bit PC, automatically locate 32-bit Python and re-launch.
    EzCAD 2.14.11 MarkEzd.dll is a 32-bit PE DLL requiring a 32-bit execution environment.
    Returns True if re-launched, False otherwise.
    """
    if getattr(sys, "frozen", False):
        return False  # Already running compiled binary (which is 32-bit PE)

    if struct.calcsize("P") * 8 == 32:
        return False  # Already in 32-bit Python!

    if os.environ.get("AEPL_RELAUNCHED_32") or "--no-relaunch" in sys.argv:
        return False

    candidates = [
        ["py", "-3.8-32"],
        ["py", "-3-32"],
    ]

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        p38 = Path(local_app_data) / "Programs" / "Python" / "Python38-32" / "python.exe"
        if p38.is_file():
            candidates.append([str(p38)])

    for drive in ["C", "D"]:
        p = Path(f"{drive}:/Python38-32/python.exe")
        if p.is_file():
            candidates.append([str(p)])

    for cmd in candidates:
        try:
            res = subprocess.run(
                cmd + ["-c", "import struct; print(struct.calcsize('P')*8)"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip() == "32":
                log_to_file(f"Auto-detected 64-bit Python. Auto-switching to 32-bit runtime: {' '.join(cmd)}")
                env = os.environ.copy()
                env["AEPL_RELAUNCHED_32"] = "1"
                full_cmd = cmd + [str(Path(__file__).resolve())] + sys.argv[1:]
                ret = subprocess.run(full_cmd, env=env).returncode
                sys.exit(ret)
        except Exception:
            continue

    return False


def run_diagnostics():
    """Verify runtime environment, architecture, DLLs, and hardware ports."""
    print("=" * 60)
    print("AEPL RFID Laser Marking Utility — System Diagnostic Check")
    print("=" * 60)

    # 1. Architecture Check
    os_arch, proc_arch = get_system_architecture()
    print(f"[*] PC Operating System Architecture : {os_arch}")
    print(f"[*] Python Process Architecture      : {proc_arch}")

    if proc_arch == "32-bit":
        print("    [PASS] 32-bit process matches EzCAD 2.14.11 requirements.")
        if "64-bit" in os_arch:
            print("    [PASS] Running on 64-bit Windows via WOW64 subsystem (fully supported).")
    else:
        print("    [NOTICE] Running in 64-bit process. EzCAD 2.14.11 MarkEzd.dll is 32-bit.")
        print("             The app will run in SIMULATION MODE, or you can run RFID_LASER.exe")
        print("             which automatically executes in 32-bit WOW64 mode.")

    # 2. Operating System
    print(f"\n[*] Operating System Details: {sys.platform} ({os.name})")

    # 3. Companion Files Verification
    required_files = [
        "MarkEzd.dll",
        "Lmc1.dll",
        "DataMgr.dll",
        "mathlib.dll",
        "LMCMIO.dll",
        "EZCAD.CFG",
        "test.ezd",
    ]
    print("\n[*] Checking Required EzCAD Companion Files:")
    all_files_ok = True
    for fname in required_files:
        fpath = PROJECT_ROOT / fname
        if fpath.is_file():
            size = fpath.stat().st_size
            print(f"    [PASS] {fname:<15} ({size:,} bytes)")
        else:
            print(f"    [FAIL] {fname:<15} NOT FOUND at {fpath}")
            all_files_ok = False

    # 4. DLL Loadability Test
    print("\n[*] Testing MarkEzd.dll Loadability:")
    if proc_arch == "32-bit":
        try:
            import ctypes
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(str(PROJECT_ROOT))
                except Exception:
                    pass
            ctypes.windll.kernel32.SetDllDirectoryW(str(PROJECT_ROOT))
            dll_path = str(PROJECT_ROOT / "MarkEzd.dll")
            dll = ctypes.WinDLL(dll_path)
            print("    [PASS] MarkEzd.dll loaded successfully into process memory.")

            # Test export symbols
            symbols = [
                "lmc1_Initial",
                "lmc1_Initial2",
                "lmc1_LoadEzdFile",
                "lmc1_ChangeTextByName",
                "lmc1_Mark",
                "lmc1_Close",
            ]
            for sym in symbols:
                if hasattr(dll, sym):
                    print(f"    [PASS] Symbol found: {sym}")
                else:
                    print(f"    [WARN] Symbol missing: {sym}")

            # Test hardware controller detection
            try:
                hwnd = ctypes.windll.user32.CreateWindowExW(
                    0, "STATIC", "DiagOwner", 0, 0, 0, 0, 0, 0, 0, 0, 0
                )
                dll.lmc1_Initial.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p]
                dll.lmc1_Initial.restype = ctypes.c_int
                rc = dll.lmc1_Initial(str(PROJECT_ROOT), 0, ctypes.c_void_p(hwnd))
                if rc == 0:
                    print("    [PASS] EzCAD LMC1 Controller Board: DETECTED & INITIALIZED on USB.")
                    if hasattr(dll, "lmc1_Close"):
                        dll.lmc1_Close()
                elif rc in (3, 4):
                    print(f"    [NOTICE] EzCAD LMC1 Controller Board: NOT CONNECTED (rc={rc}: USB Board not found).")
                    print("             (App will run in Simulation Mode until USB board is plugged in).")
                else:
                    print(f"    [WARN] EzCAD LMC1 Controller Board initialization returned code: {rc}")
            except Exception as exc:
                print(f"    [WARN] Could not probe controller board: {exc}")
        except Exception as e:
            print(f"    [FAIL] Error loading MarkEzd.dll: {e}")
    else:
        print("    [NOTICE] In-process DLL loading bypassed in 64-bit Python.")
        print("             Simulation mode active. For real hardware marking, run RFID_LASER.exe.")

    # 5. Serial COM Ports Check
    print("\n[*] Scanning Available Serial Ports (RFID Reader):")
    try:
        from serial.tools import list_ports
        ports = list_ports.comports()
        if ports:
            for p in ports:
                print(f"    [FOUND] {p.device}: {p.description}")
        else:
            print("    [NOTICE] No active COM ports detected. Connect the RFID reader USB.")
    except Exception as e:
        print(f"    [FAIL] Could not query COM ports: {e}")

    print("=" * 60)
    print("Diagnostic complete. Log saved to activity.log.\n")


def main():
    log_to_file("Starting RFID Laser Marking Utility...")

    # Auto-detect PC version: if running in 64-bit Python, auto-relaunch with 32-bit runtime
    check_and_relaunch_for_32bit()

    # If --diag or --verify is passed in arguments
    if "--diag" in sys.argv or "--verify" in sys.argv:
        run_diagnostics()
        if "--only" in sys.argv:
            sys.exit(0)

    from ui.laser_app import RFIDLaserApp

    app = RFIDLaserApp()
    app.run()


if __name__ == "__main__":
    main()
