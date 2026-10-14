"""Standalone Launcher for AEPL RFID Laser Marking Utility with Crash Diagnostics.
Connects RFID Reader -> reads Tag ID -> updates text 't1' in EzCAD template 'test.ezd' -> marks laser.
Compatible with Windows 7 32-bit and Python 3.8 32-bit.
"""

from datetime import datetime
import os
from pathlib import Path
import struct
import sys
import traceback

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


def run_diagnostics():
    """Verify runtime environment, architecture, DLLs, and hardware ports."""
    print("=" * 60)
    print("AEPL RFID Laser Marking Utility — System Diagnostic Check")
    print("=" * 60)

    # 1. Architecture Check
    arch_bits = struct.calcsize("P") * 8
    print(f"[*] Python Process Architecture: {arch_bits}-bit")
    if arch_bits == 32:
        print("    [PASS] 32-bit architecture matches EzCAD 2.14.11 requirements.")
    else:
        print("    [FAIL] Process is not 32-bit! MarkEzd.dll requires 32-bit runtime.")

    # 2. Operating System
    print(f"[*] Operating System: {sys.platform} ({os.name})")

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
